#!/usr/bin/env bash
set -euo pipefail

echo "=== [m3 regression taifex preflight v1] start $(date -Iseconds) ==="

python3 - <<'PY2'
from execution.taifex_preflight_v1 import check_taifex_preflight

def case(name, **kw):
    v = check_taifex_preflight(**kw)
    print(f"[CASE] {name} ok={v.ok} code={v.code} reason={v.reason}")
    return v

# B1: MARKET qty limits
v1 = case("MARKET_day_limit_ok", symbol="TMF", side="BUY", qty=10, order_type="MARKET", price=None, meta={"session_hint":"DAY"})
assert v1.ok
v2 = case("MARKET_day_limit_fail", symbol="TMF", side="BUY", qty=11, order_type="MARKET", price=None, meta={"session_hint":"DAY"})
assert (not v2.ok) and v2.code == "EXEC_TAIFEX_MKT_QTY_LIMIT"
v3 = case("MARKET_ah_limit_fail", symbol="TMF", side="BUY", qty=6, order_type="MARKET", price=None, meta={"session_hint":"AFTER_HOURS"})
assert (not v3.ok) and v3.code == "EXEC_TAIFEX_MKT_QTY_LIMIT"

# B2: MWP must have same-side limit
v4 = case("MWP_missing_best_same_fail", symbol="TMF", side="BUY", qty=1, order_type="MWP", price=None, meta={})
assert (not v4.ok) and v4.code == "EXEC_TAIFEX_MWP_NO_SAMESIDE_LIMIT"
v5 = case("MWP_best_same_ok_warn", symbol="TMF", side="BUY", qty=1, order_type="MWP", price=None, meta={"best_same_side_limit": 20000})
assert v5.ok

# B3: regime dpb risk flag blocks
v6 = case("DPB_risk_blocks", symbol="TMF", side="BUY", qty=1, order_type="LIMIT", price=20000, meta={"regime_dpb_risk": True})
assert (not v6.ok) and v6.code == "EXEC_TAIFEX_REGIME_DPB_RISK"

print("[OK] taifex preflight regression PASS")
PY2

echo "=== [m3 regression taifex preflight v1] PASS $(date -Iseconds) ==="
