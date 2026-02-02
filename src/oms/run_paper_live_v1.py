from __future__ import annotations
import argparse
import os
import sqlite3
from pathlib import Path

from src.oms.paper_oms_v1 import PaperOMS
from src.data.store_sqlite_v1 import init_db
from src.oms.paper_oms_risk_safety_wrapper_v1 import PaperOMSRiskSafetyWrapperV1
from src.risk.risk_engine_v1 import RiskEngineV1, RiskConfigV1
from src.safety.system_safety_v1 import SystemSafetyEngineV1, SafetyConfigV1
from src.market.market_metrics_from_db_v1 import get_market_metrics_from_db


def _db_counts(db_path: Path):
    con = sqlite3.connect(str(db_path))
    try:
        o = con.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        f = con.execute("SELECT COUNT(*) FROM fills").fetchone()[0]
        t = con.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
        return int(o), int(f), int(t)
    finally:
        con.close()


def _last_orders(db_path: Path, n: int = 6):
    con = sqlite3.connect(str(db_path))
    try:
        rows = con.execute(
            "SELECT id, ts, symbol, side, qty, order_type, status FROM orders ORDER BY id DESC LIMIT ?",
            (n,),
        ).fetchall()
        return rows
    finally:
        con.close()


def main():
    p = argparse.ArgumentParser(description='TMF AutoTrader paper-live runner (v1)')
    p.add_argument('--db', default=os.environ.get("TMF_DB_PATH", "runtime/data/tmf_autotrader_v1.sqlite3"), help='sqlite db path (or env TMF_DB_PATH)')
    args = p.parse_args()
    db = Path(args.db)
    db.parent.mkdir(parents=True, exist_ok=True)
    # Ensure schema exists (no-op if already initialized)
    init_db(db)
    db.parent.mkdir(parents=True, exist_ok=True)

    oms = PaperOMS(db)
    risk = RiskEngineV1(db_path=str(db), cfg=RiskConfigV1(strict_require_market_metrics=1))
    # Safety: strict by default. For offline/after-hours smoke, you may set TMF_DEV_ALLOW_STALE_BIDASK=1
    # to bypass feed-staleness guard (does NOT relax other safety checks).
    allow_stale = (os.environ.get("TMF_DEV_ALLOW_STALE_BIDASK", "0").strip() == "1")
    safety_cfg = SafetyConfigV1(
        fop_code="TMFB6",
        max_bidask_age_seconds=6*60*60,
        require_recent_bidask=(0 if allow_stale else 1),
    )
    if allow_stale:
        print("[WARN] TMF_DEV_ALLOW_STALE_BIDASK=1 -> safety.require_recent_bidask=0 (offline smoke mode)")
    safety = SystemSafetyEngineV1(db_path=str(db), cfg=safety_cfg)
    wrap = PaperOMSRiskSafetyWrapperV1(paper_oms=oms, risk=risk, safety=safety, db_path=str(db))

    # ---- Market snapshot from DB (truthy only; do NOT fabricate market_metrics) ----
    mm = get_market_metrics_from_db(db_path=str(db), fop_code="TMFB6", bars_symbol_for_atr="TMFB6", atr_n=20) or {}

    # Always keep a numeric ref_price fallback for local smoke/demo flows,
    # BUT: only populate meta['market_metrics'] when bid/ask are truly present from DB events.
    bid = float(mm.get("bid")) if mm.get("bid") is not None else 20000.0
    ask = float(mm.get("ask")) if mm.get("ask") is not None else (bid + 1.0)

    spread_points = float(mm.get("spread_points")) if mm.get("spread_points") is not None else (ask - bid)
    atr_points = (None if mm.get("atr_points") is None else float(mm.get("atr_points")))
    liquidity_score = float(mm.get("liquidity_score")) if mm.get("liquidity_score") is not None else 0.0

    market_metrics = {}
    if mm.get("bid") is not None and mm.get("ask") is not None:
        market_metrics = {
            "bid": bid,
            "ask": ask,
            "spread_points": spread_points,
            "atr_points": atr_points,
            "liquidity_score": liquidity_score,
            "source": (mm.get("source") or {}),
        }


    # CASE 1: REJECT (stop missing) -> 必須寫 DB/帶 reason code
    r1 = wrap.place_order(
        symbol="TMF",
        side="BUY",
        qty=2.0,
        order_type="MARKET",
        price=None,
        meta={
            "ref_price": bid,
            "market_metrics": market_metrics,
        },
    )
    print("[paper-live-smoke] case1_stop_missing =", r1)

    # CASE 2: PASS -> place -> fill -> store (match)
    r2 = wrap.place_order(
        symbol="TMF",
        side="BUY",
        qty=2.0,
        order_type="MARKET",
        price=None,
        meta={
            "stop_price": (bid - 50.0),  # bounded risk (<= 1500 NTD worst-case)
            "ref_price": bid,
            "market_metrics": market_metrics,
        },
    )

    # wrapper pass-through returns Order object from PaperOMS
    if isinstance(r2, dict):
        print("[paper-live-smoke] case2_rejected =", r2)
        return
    print("[paper-live-smoke] case2_pass_place =", f"status={getattr(r2,'status',None)} order_id={getattr(r2,'order_id',None)}")

    fills = oms.match(r2, market_price=(bid + 0.5), liquidity_qty=10.0, reason="paper_live_smoke_fill")
    print("[paper-live-smoke] case2_fills =", len(fills))

    o, f, t = _db_counts(db)
    print("[paper-live-smoke] db_counts orders/fills/trades =", o, f, t)
    print("[paper-live-smoke] last_orders:")
    for row in _last_orders(db, n=8):
        print(row)


if __name__ == "__main__":
    main()
