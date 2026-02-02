#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== [M2 intrade regression v1] start $(date -Iseconds) ==="

python3 - <<'PY'
import sqlite3
from pathlib import Path

from src.oms.paper_oms_v1 import PaperOMS
from src.risk.in_trade_controls_v1 import run_intrade_once, InTradeConfigV1
from src.risk.risk_engine_v1 import RiskEngineV1, RiskConfigV1
from src.oms.paper_oms_risk_wrapper_v1 import PaperOMSRiskWrapperV1

db = Path("/tmp/tmf_autotrader_intrade_regtest.sqlite3")
if db.exists():
    db.unlink()

live = Path("runtime/data/tmf_autotrader_v1.sqlite3")
if live.exists():
    db.write_bytes(live.read_bytes())

oms = PaperOMS(db)
risk = RiskEngineV1(db_path=str(db), cfg=RiskConfigV1(strict_require_market_metrics=0))
wrap = PaperOMSRiskWrapperV1(paper_oms=oms, risk=risk, db_path=str(db))

bid = 20000.0

# Open LONG with stop_price
o = wrap.place_order(
    symbol="TMF", side="BUY", qty=2.0, order_type="MARKET", price=None,
    meta={"ref_price": bid, "stop_price": bid - 50.0, "market_metrics": {"spread_points": 1.0, "atr_points": 10.0, "liquidity_score": 10.0}},
)
assert not isinstance(o, dict), f"unexpected reject: {o}"
fills = oms.match(o, market_price=bid + 0.5, liquidity_qty=10.0, reason="reg_open")
assert len(fills) == 1, "open fill missing"

# A) Stop-loss hit -> close
r = run_intrade_once(oms=oms, symbol="TMF", market_price=bid - 100.0, cfg=InTradeConfigV1(time_stop_seconds=1e9, strict_require_stop=1))
assert r["ok"] and r["action"] == "CLOSE_STOP", r

con = sqlite3.connect(str(db))
try:
    row = con.execute("SELECT reason_close, close_ts, pnl FROM trades ORDER BY id DESC LIMIT 1").fetchone()
    assert row, "no trade row"
    assert row[0] == "risk_stop", f"reason_close expected risk_stop got {row[0]}"
finally:
    con.close()

# Re-open for time-stop test
o2 = wrap.place_order(
    symbol="TMF", side="BUY", qty=2.0, order_type="MARKET", price=None,
    meta={"ref_price": bid, "stop_price": bid - 50.0},
)
assert not isinstance(o2, dict), f"unexpected reject2: {o2}"
fills2 = oms.match(o2, market_price=bid + 0.5, liquidity_qty=10.0, reason="reg_open2")
assert len(fills2) == 1, "open fill2 missing"

# B) Time-stop immediately
r2 = run_intrade_once(oms=oms, symbol="TMF", market_price=bid + 0.5, cfg=InTradeConfigV1(time_stop_seconds=0.0, strict_require_stop=1))
assert r2["ok"] and r2["action"] == "CLOSE_TIME_STOP", r2

con = sqlite3.connect(str(db))
try:
    row = con.execute("SELECT reason_close FROM trades ORDER BY id DESC LIMIT 1").fetchone()
    assert row, "no trade row2"
    assert row[0] == "risk_time_stop", f"reason_close expected risk_time_stop got {row[0]}"
finally:
    con.close()

print("[PASS] intrade regression v1 OK (stop + time-stop + reason_close)")
print("[INFO] temp_db=", str(db))
PY

echo "=== [M2 intrade regression v1] PASS $(date -Iseconds) ==="
