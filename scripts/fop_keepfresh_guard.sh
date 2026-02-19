#!/usr/bin/env bash
set -euo pipefail

# --- env bootstrap (launchd does NOT inherit your interactive shell env) ---
for f in "$HOME/tmf_autotrader/.env" "$HOME/.tmf_autotrader.env"; do
  if [ -f "$f" ]; then
    set -a
    # shellcheck disable=SC1090
    . "$f"
    set +a
  fi
done

cd "$HOME/tmf_autotrader"

log="runtime/logs/fop_keepfresh_guard.$(date +%F).log"
mkdir -p "$(dirname "$log")"

# If you want to see logs in terminal while still appending to file:
#   TMF_KEEPFRESH_STDOUT=1 ./scripts/fop_keepfresh_guard.sh
if [ "${TMF_KEEPFRESH_STDOUT:-0}" = "1" ]; then
  exec > >(tee -a "$log") 2>&1
else
  exec >> "$log" 2>&1
fi

# --- single-instance lock (stale-safe; no flock needed) ---
LOCKDIR="runtime/locks/fop_keepfresh_guard.lockdir"
PIDFILE="$LOCKDIR/pid"
mkdir -p "runtime/locks"

if mkdir "$LOCKDIR" 2>/dev/null; then
  printf "%s\n" "$$" > "$PIDFILE" 2>/dev/null || true
else
  oldpid=""
  if [ -f "$PIDFILE" ]; then
    oldpid="$(/bin/cat "$PIDFILE" 2>/dev/null || true)"
    oldpid="$(printf "%s" "$oldpid" | /usr/bin/tr -d "\r")"
  fi
  if [ -n "$oldpid" ] && /bin/kill -0 "$oldpid" 2>/dev/null; then
    echo "=== [LOCKED] another instance running; pid=$oldpid; exit 0 ==="
    exit 0
  fi
  # stale lock: cleanup then retry once
  /bin/rm -f "$PIDFILE" 2>/dev/null || true
  /bin/rmdir "$LOCKDIR" 2>/dev/null || true
  if mkdir "$LOCKDIR" 2>/dev/null; then
    printf "%s\n" "$$" > "$PIDFILE" 2>/dev/null || true
  else
    echo "=== [LOCKED] another instance running; pid=unknown; exit 0 ==="
    exit 0
  fi
fi

cleanup() {
  /bin/rm -f "$PIDFILE" 2>/dev/null || true
  /bin/rmdir "$LOCKDIR" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

# --- config ---
DB="runtime/data/tmf_autotrader_v1.sqlite3"
RAW_DIR="runtime/raw_events"
mkdir -p "$RAW_DIR"

MAX_AGE_SEC="${TMF_MAX_BIDASK_AGE_SEC:-15}"       # staleness target
REC_SECS="${TMF_KEEPFRESH_REC_SECS:-12}"          # recorder run seconds per loop
SLEEP_BETWEEN="${TMF_KEEPFRESH_SLEEP_SEC:-1}"     # throttle between loops
TARGET_CODE="${TMF_KEEPFRESH_FOP_CODE:-TMFB6}"    # keepfresh target (TMF)
ONESHOT="${TMF_KEEPFRESH_ONESHOT:-0}"

# --- market closed gate (CNY / holidays / off-hours) ---
# launchd-safe: allow operator to disable keepfresh cleanly
if [ "${TMF_KEEPFRESH_DISABLED:-0}" = "1" ]; then
  echo "=== [DISABLED] TMF_KEEPFRESH_DISABLED=1; exit 0 ==="
  exit 0
fi

# Market calendar gate (TAIFEX) — use deterministic calendar module
# Bypass with TMF_KEEPFRESH_FORCE=1 if you intentionally want to run anyway.
if [ "${TMF_KEEPFRESH_FORCE:-0}" != "1" ]; then
  out="$(python3 scripts/ops_market_calendar_status_v1.py 2>/dev/null || true)"
  # If probe fails, do NOT block keepfresh (safer when market is open)
  if printf "%s\n" "$out" | grep -q "^closed=1$"; then
    code="$(printf "%s\n" "$out" | sed -n "s/^code=//p" | head -n 1)"
    reason="$(printf "%s\n" "$out" | sed -n "s/^reason=//p" | head -n 1)"
    next="$(printf "%s\n" "$out" | sed -n "s/^next_open_day=//p" | head -n 1)"
    echo "=== [MARKET_CLOSED] ${code:-MARKET_CLOSED}; ${reason:-}; next_open_day=${next:-} ; exit 0 ==="
    exit 0
  fi
fi
             # debug: run exactly one loop then exit

session_tag() {
  local hm
  hm="$(date +%H%M)"
  if [ "$hm" -ge 1500 ] || [ "$hm" -le 0500 ]; then
    echo "NIGHT"
  else
    echo "DAY"
  fi
}

pick_raw() {
  # 1) Try parse absolute path from recorder output if present:
  #    [OK] recorder wrote: /Users/.../runtime/raw_events/shioaji_recorder.XXXX.jsonl
  local rec_out="$1"
  local p=""
  p="$(printf "%s\n" "$rec_out" \
      | /usr/bin/sed -n 's/.*recorder wrote:[[:space:]]*\(\/[^[:space:]]*shioaji_recorder\.[0-9_]*\.jsonl\).*/\1/p' \
      | /usr/bin/tail -n 1 \
      | /usr/bin/tr -d "\r" \
      || true)"
  if [ -n "$p" ] && [ -f "$p" ]; then
    echo "$p"
    return 0
  fi

  # 2) Fallback: pick newest shioaji_recorder.*.jsonl in RAW_DIR WITHOUT shell globs (avoids ARG_MAX)
  local newest=""
  newest="$(RAW_DIR="$RAW_DIR" python3 - <<'PY'
import os
raw_dir = os.environ.get("RAW_DIR","")
best = ""
best_m = -1.0
try:
    with os.scandir(raw_dir) as it:
        for e in it:
            if not e.is_file():
                continue
            n = e.name
            if not (n.startswith("shioaji_recorder.") and n.endswith(".jsonl")):
                continue
            try:
                m = e.stat().st_mtime
            except Exception:
                continue
            if m > best_m:
                best_m = m
                best = e.path
except FileNotFoundError:
    pass
print(best)
PY
)"
  newest="$(printf "%s" "$newest" | /usr/bin/tr -d "\r")"
  if [ -n "$newest" ] && [ -f "$newest" ]; then
    echo "$newest"
    return 0
  fi

  # 3) Brief wait/retry
  local i
  for i in 1 2 3 4 5; do
    /bin/sleep 0.2
    newest="$(RAW_DIR="$RAW_DIR" python3 - <<'PY'
import os
raw_dir = os.environ.get("RAW_DIR","")
best = ""
best_m = -1.0
try:
    with os.scandir(raw_dir) as it:
        for e in it:
            if not e.is_file():
                continue
            n = e.name
            if not (n.startswith("shioaji_recorder.") and n.endswith(".jsonl")):
                continue
            try:
                m = e.stat().st_mtime
            except Exception:
                continue
            if m > best_m:
                best_m = m
                best = e.path
except FileNotFoundError:
    pass
print(best)
PY
)"
    newest="$(printf "%s" "$newest" | /usr/bin/tr -d "\r")"
    if [ -n "$newest" ] && [ -f "$newest" ]; then
      echo "$newest"
      return 0
    fi
  done

  return 1
}

echo "=== [DAEMON_START] $(date '+%F %T') session=$(session_tag) target=$TARGET_CODE max_age=${MAX_AGE_SEC}s rec=${REC_SECS}s sleep=${SLEEP_BETWEEN}s oneshot=$ONESHOT ==="

while true; do
  echo "=== [LOOP] $(date '+%F %T') session=$(session_tag) target=$TARGET_CODE ==="

  # run recorder and capture its stdout/stderr for parsing
  rec_out=""
  set +e
  rec_out="$(TMF_SHIOAJI_FOP_CONTRACT_CODE="$TARGET_CODE" TMF_SHIOAJI_RUN_SECONDS="$REC_SECS" ./scripts/run_recorder.sh 2>&1)"
  rc=$?
  set -e
  echo "$rec_out"
  if [ "$rc" -ne 0 ]; then
    echo "[WARN] run_recorder.sh exit_code=$rc (continue)"
  fi

  raw=""
  if raw="$(pick_raw "$rec_out")"; then
    echo "=== [RAW_OK] $raw ==="
  else
    echo "[WARN] no raw file found after recorder; RAW_DIR=$RAW_DIR"
    echo "[HINT] newest 5 by mtime (python):"
    RAW_DIR="$RAW_DIR" python3 - <<'PY' || true
import os
raw_dir=os.environ.get("RAW_DIR","")
items=[]
try:
    with os.scandir(raw_dir) as it:
        for e in it:
            if e.is_file() and e.name.startswith("shioaji_recorder.") and e.name.endswith(".jsonl"):
                try: items.append((e.stat().st_mtime, e.path))
                except Exception: pass
except FileNotFoundError:
    pass
items.sort(reverse=True)
for m,p in items[:5]:
    print(int(m), p)
PY
    if [ "$ONESHOT" = "1" ]; then exit 13; fi
    /bin/sleep 2
    continue
  fi

  echo "=== [INGEST] $raw ==="
  python3 src/data/store_sqlite_v1.py "$DB" "$raw" || true

  echo "=== [NORMALIZE] ==="
  python3 src/data/normalize_events_v1.py || true

  echo "=== [STALE_GUARD ${MAX_AGE_SEC}s] ==="
  DB="$DB" TARGET_CODE="$TARGET_CODE" MAX_AGE_SEC="$MAX_AGE_SEC" python3 - <<'PY' || true
import os, sqlite3
from datetime import datetime, timezone
db = os.environ["DB"]
target = os.environ["TARGET_CODE"]
max_age = float(os.environ["MAX_AGE_SEC"])
con = sqlite3.connect(db)
cur = con.cursor()
cur.execute(
    "SELECT id, ts FROM events "
    "WHERE kind='bidask_fop_v1' AND json_extract(payload_json, '$.code') = ? "
    "ORDER BY ts DESC LIMIT 1",
    (target,),
)
row = cur.fetchone()
now = datetime.now(timezone.utc)
if not row:
    print(f"[STALE] now_utc={now.isoformat()} NO_ROW code={target}")
    raise SystemExit(13)
_id, _ts = row
ts = datetime.fromisoformat(_ts.replace("Z", "+00:00"))
age = (now - ts).total_seconds()
if age <= max_age:
    print(f"[OK] target={target} id={_id} ts={_ts} now_utc={now.isoformat()} age_sec={age:.3f}")
    raise SystemExit(0)
print(f"[STALE] target={target} id={_id} ts={_ts} now_utc={now.isoformat()} age_sec={age:.3f} max={max_age}")
raise SystemExit(13)
PY

  if [ "$ONESHOT" = "1" ]; then
    echo "=== [ONESHOT_DONE] exit 0 ==="
    exit 0
  fi

  /bin/sleep "$SLEEP_BETWEEN"
done
