#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

TS="$(date +%Y%m%d_%H%M%S)"
LOG="runtime/logs/m2_regression_market_quality_gates_v1.run.${TS}.log"
LAST="runtime/logs/m2_regression_market_quality_gates_v1.last.log"

python3 - <<PY | tee "$LOG"
import json, tempfile
from pathlib import Path

from src.data.store_sqlite_v1 import init_db
from src.oms.paper_oms_v1 import PaperOMS
from src.oms.paper_oms_risk_wrapper_v1 import PaperOMSRiskWrapperV1
from src.risk.risk_engine_v1 import RiskEngineV1, RiskConfigV1

tmpdir = Path(tempfile.mkdtemp(prefix="tmf_autotrader_mq_regtest_"))
db = tmpdir / "tmf_autotrader_v1_regtest.sqlite3"
init_db(db)

cfg = RiskConfigV1(
    strict_require_stop=1,
    per_trade_max_loss_ntd=1500.0,
    daily_max_loss_ntd=999999.0,  # neutralize DB-based gates for this test
    consecutive_losses_limit=999,
    cooldown_minutes_after_consecutive_losses=0,
    strict_require_market_metrics=0,
    max_spread_points=2.0,
    max_volatility_atr_points=50.0,
    min_liquidity_score=0.2,
)

risk = RiskEngineV1(db_path=str(db), cfg=cfg)
oms = PaperOMS(db_path=str(db))
w = PaperOMSRiskWrapperV1(paper_oms=oms, risk=risk, db_path=str(db))

def _status(x):
    if isinstance(x, dict):
        return x.get("status")
    return getattr(x, "status", None)

def _risk_code(x):
    # rejected path often returns dict with risk={code,...}
    if isinstance(x, dict):
        r = x.get("risk") or {}
        return r.get("code") if isinstance(r, dict) else getattr(r, "code", None)
    r = getattr(x, "risk", None)
    if r is None:
        return None
    return r.get("code") if isinstance(r, dict) else getattr(r, "code", None)

def assert_reject(code: str, meta: dict):
    r = w.place_order(
        symbol="TMF", side="BUY", qty=2.0, order_type="MARKET",
        meta={"ref_price": 20000.0, "stop_price": 19990.0, **meta},
    )
    st = _status(r)
    assert st == "REJECTED", f"expected REJECTED got {st} (type={type(r)})"
    rc = _risk_code(r)
    assert rc == code, f"expected {code} got {rc} (type={type(r)})"
    print(f"[CASE] reject {code} -> OK")

def assert_pass(meta: dict):
    r = w.place_order(
        symbol="TMF", side="BUY", qty=2.0, order_type="LIMIT", price=20000.0,
        meta={"stop_price": 19990.0, **meta},
    )
    st = _status(r)
    assert st in ("NEW", "FILLED"), f"expected NEW/FILLED got {st} (type={type(r)})"
    # On pass, risk may be absent; do not assert.
    print(f"[CASE] pass -> OK (status={st}, type={type(r).__name__})")

# A) spread too wide
assert_reject("RISK_SPREAD_TOO_WIDE", {"market_metrics": {"spread_points": 3.0, "atr_points": 10.0, "liquidity_score": 1.0}})

# B) volatility too high (ATR)
assert_reject("RISK_VOL_TOO_HIGH", {"market_metrics": {"spread_points": 1.0, "atr_points": 80.0, "liquidity_score": 1.0}})

# C) liquidity too low
assert_reject("RISK_LIQUIDITY_LOW", {"market_metrics": {"spread_points": 1.0, "atr_points": 10.0, "liquidity_score": 0.0}})

# D) all OK
assert_pass({"market_metrics": {"spread_points": 1.0, "atr_points": 10.0, "liquidity_score": 1.0}})

print(f"[OK] m2 regression market-quality gates PASS (temp db): {db}")
PY

cp -f "$LOG" "$LAST"
echo "[OK] wrote log: $LAST"
