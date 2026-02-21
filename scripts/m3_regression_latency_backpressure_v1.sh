#!/bin/bash
set -euo pipefail
cd "$HOME/tmf_autotrader"
echo "=== [m3 regression latency+backpressure v1] start $(date -Iseconds) ==="

python3 - <<'PY'
import tempfile, sqlite3, json
from pathlib import Path
from datetime import datetime, timedelta, timezone

from src.data.store_sqlite_v1 import init_db
from src.safety.system_safety_v1 import SystemSafetyEngineV1, SafetyConfigV1

tmpdir = Path(tempfile.mkdtemp(prefix="tmf_latbp_reg_"))
db = tmpdir / "t.sqlite3"
init_db(db)

# Insert a bidask event with old recv_ts so feed_age_ms will be large.
con = sqlite3.connect(str(db))
try:
    now = datetime.now(timezone.utc)
    recv = now - timedelta(seconds=2)  # 10s stale
    payload = {
        "code": "TMFB6",
        "bid": 20000.0,
        "ask": 20001.0,
        "recv_ts": recv.isoformat().replace("+00:00","Z"),
        "ingest_ts": recv.isoformat().replace("+00:00","Z"),
        "synthetic": False,
    }
    con.execute(
        "INSERT INTO events(ts, kind, payload_json, source_file, ingest_ts) VALUES(?,?,?,?,?)",
        (now.isoformat().replace("+00:00","Z"), "bidask_fop_v1", json.dumps(payload, ensure_ascii=False), "regtest_latency_bp", now.isoformat().replace("+00:00","Z"))
    )
    con.commit()
finally:
    con.close()

cfg = SafetyConfigV1(
    require_recent_bidask=1,
    reject_synthetic_bidask=1,
    fop_code="TMFB6",
    # Keep staleness guard loose so latency/backpressure logic can be the trigger.
    max_bidask_age_seconds=999999,
    require_session_open=0,
)

s = SystemSafetyEngineV1(db_path=str(db), cfg=cfg)

# Tight budgets via meta: should COOLDOWN
meta = {
    "tmf_max_feed_age_ms": 1500,  # allow 1.5s, but event is 10s old
    "tmf_backpressure_cooldown_seconds": 7,
    "broker_rtt_ms": 0,
    "oms_queue_depth": 0,
}
v1 = s.check_pre_trade(meta=meta)
print("[CASE] stale_by_latency_budget ->", v1.code, "ok=", v1.ok, "reason=", v1.reason)
assert (not v1.ok) and v1.code == "SAFETY_COOLDOWN_ACTIVE", f"expected COOLDOWN; got {v1.to_dict()}"

# Cooldown persists
v2 = s.check_pre_trade(meta=meta)
print("[CASE] cooldown_persists ->", v2.code, "ok=", v2.ok)
assert (not v2.ok) and v2.code == "SAFETY_COOLDOWN_ACTIVE"

# Extreme staleness -> KILL (backpressure governor)
meta2 = dict(meta)
meta2["tmf_backpressure_kill_on_extreme"] = 1
meta2["tmf_backpressure_cooldown_seconds"] = 0
meta2["tmf_max_feed_age_ms"] = 999999  # don't fail on budget; let bp decide

# --- CASE3 ISOLATION: use fresh DB so cooldown from case1/2 cannot leak ---
tmpdir3 = Path(tempfile.mkdtemp(prefix="tmf_latbp_reg_case3_"))
db3 = tmpdir3 / "t3.sqlite3"
init_db(db3)

con = sqlite3.connect(str(db3))
try:
    now = datetime.now(timezone.utc)
    recv = now - timedelta(seconds=10)  # 10000ms (ensure extreme -> KILL)
    payload = {
        "code": "TMFB6",
        "bid": 20000.0,
        "ask": 20001.0,
        "recv_ts": recv.isoformat().replace("+00:00","Z"),
        "ingest_ts": recv.isoformat().replace("+00:00","Z"),
        "synthetic": False,
    }
    con.execute(
        "INSERT INTO events(ts, kind, payload_json, source_file, ingest_ts) VALUES(?,?,?,?,?)",
        (now.isoformat().replace("+00:00","Z"), "bidask_fop_v1", json.dumps(payload, ensure_ascii=False), "regtest_latency_bp3", now.isoformat().replace("+00:00","Z"))
    )
    con.commit()
finally:
    con.close()

s3 = SystemSafetyEngineV1(db_path=str(db3), cfg=cfg)
v3 = s3.check_pre_trade(meta=meta2)
print("[CASE] extreme_bp_kill ->", v3.code, "ok=", v3.ok, "reason=", v3.reason)
assert (not v3.ok) and v3.code == "SAFETY_KILL_SWITCH", f"expected KILL; got {v3.to_dict()}"


print("[PASS] m3 latency+backpressure regression OK")
PY
