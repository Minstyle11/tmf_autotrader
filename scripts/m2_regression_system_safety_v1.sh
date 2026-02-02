#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
echo "=== [m2 regression system safety v1] start $(date -Iseconds) ==="

python3 - <<'PY'
import json, sqlite3, tempfile, os
from datetime import datetime, timedelta
from pathlib import Path
from src.safety.system_safety_v1 import SystemSafetyEngineV1, SafetyConfigV1

tmp = Path(tempfile.mkdtemp(prefix="tmf_autotrader_safety_regtest_")) / "safety.sqlite3"
con = sqlite3.connect(str(tmp))
try:
    con.execute("CREATE TABLE events (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, kind TEXT NOT NULL, payload_json TEXT NOT NULL, source_file TEXT NOT NULL, ingest_ts TEXT NOT NULL)")
    # fresh event (now-10s)
    now = datetime.now()
    ingest_ts = now.isoformat(timespec="milliseconds")
    fresh_ts = (now - timedelta(seconds=10)).isoformat(timespec="milliseconds")
    stale_ts = (now - timedelta(hours=10)).isoformat(timespec="milliseconds")
    payload = {"code":"TMFB6","bid_price":[20000.0],"ask_price":[20001.0],"bid_volume":[1,1,1,1,1],"ask_volume":[1,1,1,1,1]}
    con.execute("INSERT INTO events(ts,kind,payload_json,source_file,ingest_ts) VALUES(?,?,?,?,?)", (fresh_ts, "bidask_fop_v1", json.dumps(payload), "regtest_seed", ingest_ts))
    con.execute("INSERT INTO events(ts,kind,payload_json,source_file,ingest_ts) VALUES(?,?,?,?,?)", (stale_ts, "bidask_fop_v1", json.dumps(payload), "regtest_seed", ingest_ts))
    con.commit()
finally:
    con.close()

# CASE A: max_age=60s should PASS because latest is fresh
eng = SystemSafetyEngineV1(db_path=str(tmp), cfg=SafetyConfigV1(fop_code="TMFB6", max_bidask_age_seconds=60))
v = eng.check_pre_trade(meta={})
print("[CASE A] fresh feed ->", "PASS" if v.ok else ("REJECT "+v.code))
assert v.ok

# CASE B: max_age=1s should REJECT (age ~10s)
eng2 = SystemSafetyEngineV1(db_path=str(tmp), cfg=SafetyConfigV1(fop_code="TMFB6", max_bidask_age_seconds=1))
v2 = eng2.check_pre_trade(meta={})
print("[CASE B] stale feed ->", "REJECT "+v2.code)
assert (not v2.ok) and v2.code == "SAFETY_FEED_STALE"

print("[OK] m2 regression system safety PASS (temp db):", str(tmp))
PY

echo "=== [m2 regression system safety v1] PASS $(date -Iseconds) ==="
