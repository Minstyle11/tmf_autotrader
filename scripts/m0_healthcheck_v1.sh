#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

VENV_PY="./.venv/bin/python"
DB="runtime/data/tmf_autotrader_v1.sqlite3"

# If STRICT_SESSION=1, healthcheck will FAIL unless session verdict is OK_*.
STRICT_SESSION="${STRICT_SESSION:-0}"

# Market-event guard (used only when ticks exist in latest raw)
MIN_NON_SYS="${MIN_NON_SYS:-50}"

# Freshness guard between latest *tick* in latest raw vs latest bar ts_min
MAX_STALE_SECS="${MAX_STALE_SECS:-180}"   # 3 minutes

echo "=== [HC] tmf_autotrader healthcheck v1.2 ==="
echo "[HC] repo=$(pwd)"

if [[ ! -x "${VENV_PY}" ]]; then
  echo "[FATAL] missing venv python: ${VENV_PY}" >&2
  exit 2
fi
if [[ ! -f "${DB}" ]]; then
  echo "[FATAL] missing DB: ${DB}" >&2
  exit 2
fi

STRICT_SESSION="${STRICT_SESSION}" MIN_NON_SYS="${MIN_NON_SYS}" MAX_STALE_SECS="${MAX_STALE_SECS}" BYPASS_DAY_STK="${BYPASS_DAY_STK:-0}" "${VENV_PY}" - <<'PY'
import os, sqlite3, datetime

db="runtime/data/tmf_autotrader_v1.sqlite3"
con=sqlite3.connect(db)
con.row_factory=sqlite3.Row

STRICT_SESSION = int(os.environ.get("STRICT_SESSION","0"))
MIN_NON_SYS = int(os.environ.get("MIN_NON_SYS","50"))
MAX_STALE_SECS = int(os.environ.get("MAX_STALE_SECS","180"))
BYPASS_DAY_STK = int(os.environ.get("BYPASS_DAY_STK","0"))

latest = con.execute("""
SELECT id, ts, source_file, lines_total, lines_ok, lines_bad
FROM ingest_runs ORDER BY id DESC LIMIT 1
""").fetchone()
if not latest:
    print("[FATAL] no ingest_runs found")
    raise SystemExit(2)

src = latest["source_file"]
print(f"[OK] db={db}")
print(f"[OK] latest_raw={src}")
print("=== [HC] last ingest ===")
print(dict(latest))

def count_tbl(name: str) -> int:
    return con.execute(f"SELECT COUNT(1) FROM {name}").fetchone()[0]

def has_tbl(name: str) -> bool:
    return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(name,)).fetchone() is not None

events_n = count_tbl("events")
norm_n   = count_tbl("norm_ticks") if has_tbl("norm_ticks") else -1
bars_n   = count_tbl("bars_1m") if has_tbl("bars_1m") else -1

print("=== [HC] table counts ===")
print("events =", events_n)
print("norm_ticks =", norm_n)
print("bars_1m =", bars_n)

# Latest raw ts range (all events)
r = con.execute("""
SELECT MIN(ts) AS min_ts, MAX(ts) AS max_ts, COUNT(1) AS n
FROM events WHERE source_file=?
""",(src,)).fetchone()
min_ts, max_ts, n = r["min_ts"], r["max_ts"], r["n"]
print("=== [HC] latest raw ts range (all events) ===")
print({"min_ts": min_ts, "max_ts": max_ts, "n": n})

# non-sys events (latest raw)
non_sys = con.execute("""
SELECT COUNT(1) FROM events
WHERE source_file=? AND kind NOT LIKE 'session_%'
""",(src,)).fetchone()[0]
print("=== [HC] non_sys_events (latest raw) ===")
print("non_sys_events =", non_sys)

# tick events (latest raw) — bars are built from ticks, so use tick timestamp for freshness/session inference
rt = con.execute("""
SELECT MIN(ts) AS min_tick_ts, MAX(ts) AS max_tick_ts, COUNT(1) AS n_tick
FROM events
WHERE source_file=? AND kind LIKE 'tick_%'
""",(src,)).fetchone()
min_tick_ts, max_tick_ts, n_tick = rt["min_tick_ts"], rt["max_tick_ts"], rt["n_tick"]
print("=== [HC] latest raw tick ts range ===")
print({"min_tick_ts": min_tick_ts, "max_tick_ts": max_tick_ts, "n_tick": n_tick})

# bars stats
bad = 0
max_bar_ts = None
max_bar_dt = None

def parse_iso(s):
    if not s: return None
    try:
        if "." in s:
            s = s.split(".")[0]
        return datetime.datetime.fromisoformat(s)
    except Exception:
        return None

if bars_n > 0:
    b = con.execute("SELECT MIN(ts_min) AS min_ts_min, MAX(ts_min) AS max_ts_min, COUNT(1) AS n FROM bars_1m").fetchone()
    print("=== [HC] bars ts_min range ===")
    print(dict(b))
    max_bar_ts = b["max_ts_min"]
    max_bar_dt = parse_iso(max_bar_ts)

    print("=== [HC] latest ts_min by symbol ===")
    rows = con.execute("""
    SELECT symbol, asset_class, MAX(ts_min) AS last_ts_min, COUNT(1) AS n
    FROM bars_1m
    GROUP BY symbol, asset_class
    ORDER BY asset_class, symbol
    """).fetchall()
    for row in rows:
        print(row["asset_class"], row["symbol"], row["last_ts_min"], row["n"])

    bad = con.execute("""
    SELECT COUNT(1)
    FROM bars_1m
    WHERE ts_min IS NULL OR symbol IS NULL
       OR o IS NULL OR h IS NULL OR l IS NULL OR c IS NULL
       OR h < l OR o < l OR o > h OR c < l OR c > h
    """).fetchone()[0]
    print("=== [HC] null/invalid checks ===")
    print("bad_rows =", bad)

# session verdict (tick-based, session-aware)
status = "UNKNOWN"
notes = []

max_tick_dt = parse_iso(max_tick_ts)

# Tick split in latest raw
n_tick_fop = con.execute(
    "SELECT COUNT(1) FROM events WHERE source_file=? AND kind='tick_fop_v1'",
    (src,)
).fetchone()[0]
n_tick_stk = con.execute(
    "SELECT COUNT(1) FROM events WHERE source_file=? AND kind='tick_stk_v1'",
    (src,)
).fetchone()[0]

# Session bucket inference by latest tick timestamp (assumes ts is local time)
bucket = "UNKNOWN"
if max_tick_dt:
    t = max_tick_dt.time()
    # TW day session roughly 08:30–14:00 (covers stock 09:00–13:30 and futures day margin)
    if (datetime.time(8,30) <= t < datetime.time(14,0)):
        bucket = "DAY"
    # Futures night session roughly 15:00–05:00
    elif (t >= datetime.time(15,0)) or (t < datetime.time(5,0)):
        bucket = "NIGHT"
    else:
        bucket = "OFF"

if n_tick == 0:
    status = "WARN_NO_TICKS_IN_LATEST_RAW"
    notes.append("latest raw has no tick_* events; recorder likely out-of-session or too short")
else:
    notes.append(f"tick_split_fop={n_tick_fop},stk={n_tick_stk}")
    notes.append(f"session_bucket={bucket}")
    if bucket == "DAY" and n_tick_stk == 0 and BYPASS_DAY_STK == 0:
        status = "FATAL_NO_STK_TICKS_DURING_DAY"
        notes.append("DAY bucket requires tick_stk_v1 > 0; set BYPASS_DAY_STK=1 to bypass")
    elif bucket == "DAY" and n_tick_stk == 0 and BYPASS_DAY_STK == 1:
        status = "WARN_NO_STK_TICKS_DURING_DAY"
        notes.append("DAY bucket expects tick_stk_v1; BYPASS_DAY_STK=1 enabled")
    elif max_tick_dt and max_bar_dt:
        delta = (max_tick_dt - max_bar_dt).total_seconds()
        notes.append(f"delta_tick_minus_bars_secs={int(delta)}")
        if delta > MAX_STALE_SECS:
            status = "WARN_BARS_STALE_VS_TICKS"
        else:
            # If we have ticks and bars are fresh, then non_sys threshold is meaningful
            if non_sys >= MIN_NON_SYS:
                status = "OK_MARKET_SESSION_LIKELY"
            else:
                status = "WARN_LOW_MARKET_EVENTS"
    else:
        status = "WARN_CANNOT_DETERMINE_SESSION"
        notes.append("missing max_tick_dt or max_bar_dt")

print("=== [HC] session verdict ===")
print("status =", status)
if notes:
    print("notes =", "; ".join(notes))

if status.startswith("FATAL_"):
    print("\n[FATAL] HEALTHCHECK FAIL (day_stk)")
    raise SystemExit(5)


print("=== [HC] last ingest_runs (top5) ===")

rows = con.execute("""
SELECT ts, lines_total, lines_ok, lines_bad, substr(sha256,1,10) AS sha10
FROM ingest_runs ORDER BY id DESC LIMIT 5
""").fetchall()
for row in rows:
    print((row["ts"], row["lines_total"], row["lines_ok"], row["lines_bad"], row["sha10"]))

# Final gate:
#  - pipeline correctness: tables exist + bar rows not invalid
#  - optional strict session: require OK_*
pipeline_ok = (events_n >= 0) and (bars_n == -1 or bad == 0)
session_ok = status.startswith("OK_")

if not pipeline_ok:
    print("\n[FATAL] HEALTHCHECK FAIL (pipeline)")
    raise SystemExit(3)

if STRICT_SESSION == 1 and not session_ok:
    print("\n[FATAL] HEALTHCHECK FAIL (session)")
    raise SystemExit(4)

if session_ok:
    print("\n[OK] HEALTHCHECK PASS (market)")
else:
    print("\n[OK] HEALTHCHECK PASS (pipeline)  [WARN] see session verdict above")

con.close()
PY
