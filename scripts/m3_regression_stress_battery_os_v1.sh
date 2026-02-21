#!/usr/bin/env bash
set -euo pipefail
echo "=== [m3 regression stress-battery os v1] start $(date -Iseconds) ==="
python3 - <<'PY'
from risk.options.stress_battery import run_stress_battery, ContractSpec
portfolio = {
    "positions": [{"symbol":"TMF","side":"LONG","qty":2,"entry_price":31775.0}],
    "cash_ntd": 800000.0,
}
specs = [ContractSpec(symbol="TMF", point_value_ntd=10.0, margin_per_contract_ntd=60000.0)]
r = run_stress_battery(
    portfolio_state=portfolio,
    contract_specs=specs,
    gate_max_loss_ntd=50000.0,
    gate_max_margin_ratio=0.5,
)
assert r.details["code"] == "OK", r.details
assert r.worst_loss_ntd >= 0
assert 0 <= r.worst_margin_ratio < 1
print("[OK] stress_battery_v1 regression PASS")
print("worst_loss_ntd=", r.worst_loss_ntd)
print("worst_margin_ratio=", r.worst_margin_ratio)
PY
echo "=== [m3 regression stress-battery os v1] PASS $(date -Iseconds) ==="
