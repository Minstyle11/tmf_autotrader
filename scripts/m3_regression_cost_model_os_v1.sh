#!/bin/bash
set -euo pipefail
cd "$HOME/tmf_autotrader"
echo "=== [m3 regression cost+slippage os v1] start $(date -Iseconds) ==="

python3 - <<'PY'
from src.cost.cost_model_v1 import CostModelV1, FeeSpecV1, TAX_RATE_V1, MULTIPLIER_BY_SYMBOL_V1
from src.sim.slippage_model_v1 import calc_slippage_points, apply_slippage, SlippageSpec

cm = CostModelV1()

# -------------------------
# [A] cost_model_v1 sanity
# -------------------------
symbol = "TMF"
price  = 20000.0
qty    = 2

# contract value
v = cm.calc_contract_value_ntd(price=price, symbol=symbol, qty=qty)
assert v == 400000.0, f"contract_value mismatch: {v}"

# expected round-trip cost (uses defaults inside CostModelV1)
# per side fee = 4.8 + 3.2 + 0.0 = 8.0
# round trip fee per contract = 16.0
# tax per side = notional * 0.00002 = 200000*0.00002=4.0 => round trip tax=8.0
# total per contract = 24.0 ; qty=2 => 48.0
c = cm.calc_round_trip_cost_ntd(price=price, symbol=symbol, qty=qty)
assert abs(c["total_cost_ntd"] - 48.0) < 1e-9, f"total_cost_ntd mismatch: {c}"
assert abs(c["fee_ntd"] - 32.0) < 1e-9, f"fee_ntd mismatch: {c}"
assert abs(c["tax_ntd"] - 16.0) < 1e-9, f"tax_ntd mismatch: {c}"
assert c["details"]["qty"] == qty
assert c["details"]["multiplier"] == MULTIPLIER_BY_SYMBOL_V1[symbol]
assert c["details"]["tax_rate"] == TAX_RATE_V1

# invalid inputs
try:
    cm.calc_contract_value_ntd(price=0, symbol=symbol, qty=1)
    raise AssertionError("expected ValueError for price<=0")
except ValueError:
    pass

try:
    cm.calc_contract_value_ntd(price=price, symbol=symbol, qty=0)
    raise AssertionError("expected ValueError for qty<=0")
except ValueError:
    pass

try:
    cm.calc_contract_value_ntd(price=price, symbol="NOPE", qty=1)
    raise AssertionError("expected KeyError for unknown symbol")
except KeyError:
    pass

print("[OK] cost_model_v1 regression PASS")

# -------------------------
# [B] slippage_model_v1 sanity
# -------------------------
# default fixed 1.0 point
slp = calc_slippage_points(price=price, symbol=symbol, side="BUY", qty=qty)
assert abs(slp - 1.0) < 1e-9, f"slippage_points mismatch: {slp}"

buy_px  = apply_slippage(price=price, symbol=symbol, side="BUY", qty=qty)
sell_px = apply_slippage(price=price, symbol=symbol, side="SELL", qty=qty)
assert abs(buy_px - (price + 1.0)) < 1e-9, f"buy_exec mismatch: {buy_px}"
assert abs(sell_px - (price - 1.0)) < 1e-9, f"sell_exec mismatch: {sell_px}"

# proportional bps + max cap
spec = SlippageSpec(fixed_points=0.5, bps=200.0, max_points=10.0)  # 200bp = 2%
# prop=20000*0.02=400 > cap 10
slp2 = calc_slippage_points(price=price, symbol=symbol, side="BUY", qty=qty, spec_override=spec)
assert abs(slp2 - 10.0) < 1e-9, f"slippage cap mismatch: {slp2}"

# invalid side
try:
    calc_slippage_points(price=price, symbol=symbol, side="HOLD", qty=1)
    raise AssertionError("expected ValueError for invalid side")
except ValueError:
    pass

print("[OK] slippage_model_v1 regression PASS")
print("[OK] m3 cost+slippage regression PASS")
PY

echo "=== [m3 regression cost+slippage os v1] PASS $(date -Iseconds) ==="
