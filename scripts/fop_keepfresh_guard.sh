#!/usr/bin/env bash
set -euo pipefail

# --- env bootstrap (launchd does NOT inherit your interactive shell env) ---
# Prefer repo-local env file, then user-level env file.
# Supports KEY=VALUE style; export all via set -a.
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

# --- single-instance lock (no flock needed) ---
LOCKDIR="runtime/locks/fop_keepfresh_guard.lockdir"
mkdir -p "runtime/locks"
if ! mkdir "$LOCKDIR" 2>/dev/null; then
  echo "=== [LOCKED] another instance running; exit 0 ===" >> "$log"
  exit 0
fi
cleanup() { rmdir "$LOCKDIR" 2>/dev/null || true; }
trap cleanup EXIT INT TERM

# --- config ---
DB="runtime/data/tmf_autotrader_v1.sqlite3"
RAW_DIR="runtime/raw_events"
mkdir -p "$RAW_DIR"

MAX_AGE_SEC="${TMF_MAX_BIDASK_AGE_SEC:-15}"      # safety target
REC_SECS="${TMF_KEEPFRESH_REC_SECS:-12}"         # recorder run seconds per loop
SLEEP_BETWEEN="${TMF_KEEPFRESH_SLEEP_SEC:-1}"    # throttle between loops
TARGET_CODE="${TMF_KEEPFRESH_FOP_CODE:-TMFB6}"   # keepfresh target (TMF)

hm="$(date +%H%M)"
sess="DAY"
if [ "$hm" -ge 1500 ] || [ "$hm" -le 0500 ]; then sess="NIGHT"; fi

echo "=== [DAEMON_START] $(date '+%F %T') session=$sess hm=$hm target=$TARGET_CODE max_age=${MAX_AGE_SEC}s rec=${REC_SECS}s ===" >> "$log"

# daemon loop: keep producing fresh TMF bidask/tick into sqlite
while true; do
  hm="$(date +%H%M)"
  sess="DAY"
  if [ "$hm" -ge 1500 ] || [ "$hm" -le 0500 ]; then sess="NIGHT"; fi

  echo "=== [LOOP] $(date '+%F %T') session=$sess hm=$hm target=$TARGET_CODE ===" >> "$log"

  TMF_SHIOAJI_FOP_CONTRACT_CODE="$TARGET_CODE" TMF_SHIOAJI_RUN_SECONDS="$REC_SECS" ./scripts/run_recorder.sh >> "$log" 2>&1 || true

  raw="$(ls -1t runtime/raw_events/shioaji_recorder.*.jsonl 2>/dev/null | head -n 1 || true)"
  if [ -z "${raw:-}" ]; then
    echo "[WARN] no raw file found; sleep 2s" >> "$log"
    sleep 2
    continue
  fi

  echo "=== [INGEST] $raw ===" >> "$log"
  python3 src/data/store_sqlite_v1.py "$DB" "$raw" >> "$log" 2>&1 || true

  echo "=== [NORMALIZE] ===" >> "$log"
  python3 src/data/normalize_events_v1.py >> "$log" 2>&1 || true

  echo "=== [STALE_GUARD ${MAX_AGE_SEC}s] ===" >> "$log"
  DB="$DB" TARGET_CODE="$TARGET_CODE" MAX_AGE_SEC="$MAX_AGE_SEC" python3 - <<'PY' >> "$log" 2>&1 || true
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
# tolerate either Z or offset; assume Z if missing tzinfo
ts = datetime.fromisoformat(_ts.replace("Z", "+00:00"))
age = (now - ts).total_seconds()

if age <= max_age:
    print(f"[OK] target={target} id={_id} ts={_ts} now_utc={now.isoformat()} age_sec={age:.3f}")
    raise SystemExit(0)
else:
    print(f"[STALE] target={target} id={_id} ts={_ts} now_utc={now.isoformat()} age_sec={age:.3f} max={max_age}")
    raise SystemExit(13)
PY

  sleep "$SLEEP_BETWEEN"
done
