#!/bin/bash
set -euo pipefail
cd "$HOME/tmf_autotrader"
echo "=== [m3 regression latency+backpressure os v1] start $(date -Iseconds) ==="

python3 - <<'PY'
from ops.latency.latency_budget import LatencyBudgetV1
from ops.latency.backpressure_governor import BackpressureConfigV1, decide

lb = LatencyBudgetV1(max_feed_age_ms=1500, max_broker_rtt_ms=1200, max_oms_queue_depth=50)
cfg = BackpressureConfigV1(cooldown_seconds=30, kill_on_extreme=1)

# CASE 1: OK
m1 = {"feed_age_ms": 0, "broker_rtt_ms": 0, "oms_queue_depth": 0}
v1 = lb.check(m1)
d1 = decide(m1, cfg)
print("[CASE1] budget=", v1, "bp=", d1)
assert v1["ok"] is True and d1.ok is True and d1.action == "ALLOW"

# CASE 2: budget reject (feed too old)
m2 = {"feed_age_ms": 2000, "broker_rtt_ms": 0, "oms_queue_depth": 0}
v2 = lb.check(m2)
print("[CASE2] budget=", v2)
assert v2["ok"] is False and v2["code"] == "LAT_FEED_TOO_OLD"

# CASE 3: backpressure cooldown (mild nonzero)
m3 = {"feed_age_ms": 10, "broker_rtt_ms": 0, "oms_queue_depth": 0}
d3 = decide(m3, cfg)
print("[CASE3] bp=", d3)
assert d3.ok is False and d3.action == "COOLDOWN" and d3.code == "BP_COOLDOWN"

# CASE 4: backpressure kill (extreme)
m4 = {"feed_age_ms": 6000, "broker_rtt_ms": 0, "oms_queue_depth": 0}
d4 = decide(m4, cfg)
print("[CASE4] bp=", d4)
assert d4.ok is False and d4.action == "KILL" and d4.code == "BP_EXTREME"

print("[OK] m3 latency+backpressure regression PASS")
PY

echo "=== [m3 regression latency+backpressure os v1] PASS $(date -Iseconds) ==="
