from __future__ import annotations
import sqlite3


def _show_result(label: str, r):
    # Support both dict-like and object-like results.
    if isinstance(r, dict):
        status = r.get("status", "?")
        ok = r.get("ok", "?")
        reason = r.get("reason", r.get("code", ""))
        print(f"[demo] {label} = {status} ok={ok} reason={reason} raw={r}")
        return
    status = getattr(r, "status", "?")
    ok = getattr(r, "ok", "?")
    reason = getattr(r, "reason", getattr(r, "code", ""))
    # dataclass __repr__ is fine; otherwise fallback to type
    try:
        raw = r
    except Exception:
        raw = f"<{type(r).__name__}>"
    print(f"[demo] {label} = {status} ok={ok} reason={reason} raw={raw}")

from pathlib import Path

from src.risk.risk_engine_v1 import RiskEngineV1, RiskConfigV1
from src.oms.paper_oms_v1 import PaperOMS
from src.oms.paper_oms_risk_wrapper_v1 import PaperOMSRiskWrapperV1

DB = "runtime/data/tmf_autotrader_v1.sqlite3"

def count_tbl(con, name):
    return con.execute(f"SELECT COUNT(1) FROM {name}").fetchone()[0]

def main():
    # Strict mode: require stop, enforce loss limits
    cfg = RiskConfigV1(
        strict_require_stop=1,
        per_trade_max_loss_ntd=500.0,     # small to force a rejection demo
        daily_max_loss_ntd=5000.0,
        consecutive_losses_limit=3,
        cooldown_minutes_after_consecutive_losses=30,
        max_qty_per_order=2.0,
    )
    risk = RiskEngineV1(db_path=DB, cfg=cfg)
    oms = PaperOMS(db_path=DB)
    w = PaperOMSRiskWrapperV1(paper_oms=oms, risk=risk, db_path=DB)

    # 1) Reject: missing stop_price
    r1 = w.place_order(symbol="TMF", side="BUY", qty=2, order_type="MARKET", price=None, meta={"ref_price": 20000.0})
    print("[demo] reject_missing_stop =", r1["status"], r1["risk"]["code"])

    # 2) Reject: stop exists but risk too high (entry-stop)*qty*pv
    r2 = w.place_order(symbol="TMF", side="BUY", qty=2, order_type="LIMIT", price=20000.0, meta={"stop_price": 19950.0})
    print("[demo] reject_risk_too_high =", r2["status"], r2["risk"]["code"])

    # 3) Accept: tight stop within per-trade max loss
    r3 = w.place_order(symbol="TMF", side="BUY", qty=2, order_type="LIMIT", price=20000.0, meta={"stop_price": 19990.0})
    _show_result("accept_order_ok", r3)

    # DB proof
    import sqlite3
    con = sqlite3.connect(DB)
    try:
        orders = count_tbl(con, "orders")
        fills  = count_tbl(con, "fills")
        trades = count_tbl(con, "trades")
        print("[demo] db_counts orders/fills/trades =", orders, fills, trades)
        rows = con.execute(
            "SELECT id, ts, symbol, side, qty, order_type, status FROM orders ORDER BY id DESC LIMIT 6"
        ).fetchall()
        print("[demo] last_orders:")
        for row in rows:
            print(tuple(row))
    finally:
        con.close()
if __name__ == "__main__":
    main()
