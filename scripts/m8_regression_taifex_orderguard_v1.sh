#!/usr/bin/env bash
set -euo pipefail

python3 - <<'PY'
from datetime import datetime
from execution.taifex_preflight_v1 import check_taifex_preflight

def assert_eq(a,b,msg):
    if a!=b:
        raise SystemExit(f"[FAIL] {msg}: got={a} expected={b}")

def run(name, **kw):
    v = check_taifex_preflight(**kw)
    return v

# REGULAR MARKET: max 10
v = run("REGULAR market qty=10", code="TMFB6", order_type="MARKET", qty=10,
        now=datetime(2026,2,23,9,0,0), meta={})
assert_eq(v.ok, True, "REGULAR market qty=10 should OK")
assert_eq(v.details.get("max_per_order"), 10, "REGULAR market max should 10")

v = run("REGULAR market qty=11", code="TMFB6", order_type="MARKET", qty=11,
        now=datetime(2026,2,23,9,0,0), meta={"allow_split": True})
assert_eq(v.ok, False, "REGULAR market qty=11 should REJECT")
assert_eq(v.code, "EXEC_TAIFEX_MKT_QTY_LIMIT", "REGULAR market exceed code")
assert_eq(v.details.get("suggested_splits"), [10,1], "REGULAR market split plan")

# AFTER_HOURS MARKET: max 5
v = run("AFTER_HOURS market qty=5", code="TMFB6", order_type="MARKET", qty=5,
        now=datetime(2026,2,23,15,30,0), meta={})
assert_eq(v.ok, True, "AFTER_HOURS market qty=5 should OK")
assert_eq(v.details.get("max_per_order"), 5, "AFTER_HOURS market max should 5")

v = run("AFTER_HOURS market qty=6", code="TMFB6", order_type="MARKET", qty=6,
        now=datetime(2026,2,23,15,30,0), meta={"allow_split": True})
assert_eq(v.ok, False, "AFTER_HOURS market qty=6 should REJECT")
assert_eq(v.code, "EXEC_TAIFEX_MKT_QTY_LIMIT", "AFTER_HOURS market exceed code")
assert_eq(v.details.get("suggested_splits"), [5,1], "AFTER_HOURS market split plan")

# LIMIT (index futures): max 100
v = run("LIMIT qty=101", code="TMFB6", order_type="LIMIT", qty=101,
        now=datetime(2026,2,23,9,0,0), meta={"allow_split": True})
assert_eq(v.ok, False, "LIMIT qty=101 should REJECT")
assert_eq(v.details.get("max_per_order"), 100, "LIMIT max should 100")
assert_eq(v.details.get("suggested_splits"), [100,1], "LIMIT split plan")

print("[PASS] m8_regression_taifex_orderguard_v1")
PY
