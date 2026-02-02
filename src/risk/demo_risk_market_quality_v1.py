from __future__ import annotations
from pathlib import Path

from src.data.store_sqlite_v1 import init_db
from src.oms.paper_oms_v1 import PaperOMS
from src.oms.paper_oms_risk_wrapper_v1 import PaperOMSRiskWrapperV1
from src.risk.risk_engine_v1 import RiskEngineV1, RiskConfigV1


def main():
    db = Path("runtime/data/tmf_autotrader_v1.sqlite3")
    db.parent.mkdir(parents=True, exist_ok=True)
    init_db(db)

    # Make thresholds intentionally tight for demo visibility.
    cfg = RiskConfigV1(
        strict_require_stop=1,
        per_trade_max_loss_ntd=1500.0,
        daily_max_loss_ntd=5000.0,
        consecutive_losses_limit=3,
        cooldown_minutes_after_consecutive_losses=30,
        strict_require_market_metrics=0,
        max_spread_points=2.0,
        max_volatility_atr_points=50.0,
        min_liquidity_score=0.2,
    )

    risk = RiskEngineV1(db_path=str(db), cfg=cfg)
    oms = PaperOMS(db_path=str(db))
    w = PaperOMSRiskWrapperV1(paper_oms=oms, risk=risk, db_path=str(db))

    # 1) Reject: spread too wide
    r1 = w.place_order(symbol="TMF", side="BUY", qty=2.0, order_type="MARKET",
                       meta={"ref_price": 20000.0, "stop_price": 19990.0, "market_metrics": {"spread_points": 3.0, "atr_points": 10.0, "liquidity_score": 1.0}})
    print("[demo] reject_spread = ", r1.get("status"), r1.get("risk", {}).get("code"))

    # 2) Reject: volatility too high (ATR)
    r2 = w.place_order(symbol="TMF", side="BUY", qty=2.0, order_type="MARKET",
                       meta={"ref_price": 20000.0, "stop_price": 19990.0, "market_metrics": {"spread_points": 1.0, "atr_points": 80.0, "liquidity_score": 1.0}})
    print("[demo] reject_vol = ", r2.get("status"), r2.get("risk", {}).get("code"))

    # 3) Reject: liquidity too low
    r3 = w.place_order(symbol="TMF", side="BUY", qty=2.0, order_type="MARKET",
                       meta={"ref_price": 20000.0, "stop_price": 19990.0, "market_metrics": {"spread_points": 1.0, "atr_points": 10.0, "liquidity_score": 0.0}})
    print("[demo] reject_liq = ", r3.get("status"), r3.get("risk", {}).get("code"))

    # 4) Accept: all OK
    r4 = w.place_order(symbol="TMF", side="BUY", qty=2.0, order_type="LIMIT", price=20000.0,
                       meta={"stop_price": 19990.0, "market_metrics": {"spread_points": 1.0, "atr_points": 10.0, "liquidity_score": 1.0}})
    status = (r4.get("status", "NEW") if isinstance(r4, dict) else getattr(r4, "status", "NEW"))
    okflag = (r4.get("ok", True) if isinstance(r4, dict) else True)
    print("[demo] accept_ok = ", status, "ok" if okflag else "bad")
if __name__ == "__main__":
    main()
