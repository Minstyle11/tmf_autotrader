from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

from src.oms.paper_oms_v1 import PaperOMS
from src.oms.paper_oms_risk_wrapper_v1 import PaperOMSRiskWrapperV1
from src.risk.risk_engine_v1 import RiskEngineV1, RiskConfigV1
from src.market.market_metrics_from_db_v1 import get_market_metrics_from_db

DB_PATH = "runtime/data/tmf_autotrader_v1.sqlite3"

def _now_ms() -> str:
    return datetime.now().isoformat(timespec="milliseconds")

def _seed_trade(pnl: float, *, seed: str, close_dt: datetime) -> None:
    con = sqlite3.connect(DB_PATH)
    try:
        open_ts = (close_dt - timedelta(minutes=5)).isoformat(timespec="milliseconds")
        close_ts = close_dt.isoformat(timespec="milliseconds")
        con.execute(
            "INSERT INTO trades(open_ts, close_ts, symbol, side, qty, entry, exit, pnl, pnl_pct, reason_open, reason_close, meta_json) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                open_ts,
                close_ts,
                "TMF",
                "BUY",
                1.0,
                32600.0,
                32500.0,
                float(pnl),
                -0.003,
                seed,
                seed,
                json.dumps({"seed": seed}, ensure_ascii=False),
            ),
        )
        con.commit()
    finally:
        con.close()

def _clean_seed(prefix: str) -> int:
    """
    Delete seed trades inserted by this smoke script.
    We only delete rows whose meta_json indicates {"seed": "<prefix>"} (exact match).
    Prefer SQLite JSON1 (json_extract) when available; fallback to LIKE.
    """
    con = sqlite3.connect(DB_PATH)
    try:
        try:
            cur = con.execute("DELETE FROM trades WHERE json_extract(meta_json,'$.seed') = ?", (prefix,))
        except Exception:
            # fallback (JSON1 not available)
            cur = con.execute("DELETE FROM trades WHERE meta_json LIKE ?", (f'%\"seed\": \"{prefix}\"%',))
        con.commit()
        return int(cur.rowcount)
    finally:
        con.close()

def _today_realized_pnl() -> float:
    con = sqlite3.connect(DB_PATH)
    try:
        day = datetime.now().strftime("%Y-%m-%d")
        s = con.execute(
            "SELECT COALESCE(SUM(pnl),0) FROM trades WHERE close_ts IS NOT NULL AND close_ts LIKE ?",
            (day + "%",),
        ).fetchone()[0]
        return float(s)
    finally:
        con.close()

def _make_market_metrics() -> dict:
    mm = get_market_metrics_from_db(db_path=DB_PATH, fop_code="TMFB6", bars_symbol_for_atr="TMFB6", atr_n=20) or {}
    bid = float(mm.get("bid", 20000.0))
    ask = float(mm.get("ask", bid + 1.0))
    spread_points = float(mm.get("spread_points", ask - bid))
    atr_points = float(mm.get("atr_points", 50.0))
    liquidity_score = float(mm.get("liquidity_score", 10.0))
    return {
        "bid": bid,
        "ask": ask,
        "spread_points": spread_points,
        "atr_points": atr_points,
        "liquidity_score": liquidity_score,
        "source": mm.get("source"),
    }

def _expect(code: str, got: dict, label: str) -> int:
    ok = (isinstance(got, dict) and (got.get("risk") or {}).get("code") == code)
    print(f"[TEST] {label}: expected={code} got={(got.get('risk') or {}).get('code') if isinstance(got, dict) else type(got)} -> {'PASS' if ok else 'FAIL'}")
    if not ok:
        print("       payload =", got)
        return 1
    return 0

def main() -> int:
    db = Path(DB_PATH)
    db.parent.mkdir(parents=True, exist_ok=True)

    oms = PaperOMS(db)
    risk = RiskEngineV1(db_path=str(db), cfg=RiskConfigV1(strict_require_market_metrics=1))
    wrap = PaperOMSRiskWrapperV1(paper_oms=oms, risk=risk, db_path=str(db))

    mm = _make_market_metrics()
    bid = float(mm["bid"])

    fails = 0

    # A) stop required
    r = wrap.place_order(
        symbol="TMF", side="BUY", qty=2.0, order_type="MARKET", price=None,
        meta={"ref_price": bid, "market_metrics": mm},
    )
    fails += _expect("RISK_STOP_REQUIRED", r, "stop_required")

    # B) market metrics required (stop provided but market_metrics missing)
    r = wrap.place_order(
        symbol="TMF", side="BUY", qty=2.0, order_type="MARKET", price=None,
        meta={"ref_price": bid, "stop_price": bid - 50.0},  # 50pt risk => 1000 NTD for qty=2 (OK), but missing metrics -> reject by metrics gate
    )
    fails += _expect("RISK_MARKET_METRICS_REQUIRED", r, "market_metrics_required")

    # C) per-trade max loss (need stop far away; TMF pv=10, qty=2 -> >1500 requires loss_points>75)
    r = wrap.place_order(
        symbol="TMF", side="BUY", qty=2.0, order_type="MARKET", price=None,
        meta={"ref_price": bid, "stop_price": bid - 500.0, "market_metrics": mm},
    )
    fails += _expect("RISK_PER_TRADE_MAX_LOSS", r, "per_trade_max_loss")

    # D) daily max loss
    _clean_seed("daily_max_loss_gate")
    _clean_seed("consec_loss_gate")
    _seed_trade(-6000.0, seed="daily_max_loss_gate", close_dt=datetime.now())
    print("[INFO] today_realized_pnl_after_seed =", _today_realized_pnl())
    r = wrap.place_order(
        symbol="TMF", side="BUY", qty=2.0, order_type="MARKET", price=None,
        meta={"ref_price": bid, "stop_price": bid - 50.0, "market_metrics": mm},
    )
    fails += _expect("RISK_DAILY_MAX_LOSS", r, "daily_max_loss")

    # E) consecutive losses cooldown (3 losses then attempt within cooldown)
    _clean_seed("daily_max_loss_gate")
    _clean_seed("consec_loss_gate")
    now = datetime.now()
    _seed_trade(-100.0, seed="consec_loss_gate", close_dt=now - timedelta(minutes=3))
    _seed_trade(-100.0, seed="consec_loss_gate", close_dt=now - timedelta(minutes=2))
    _seed_trade(-100.0, seed="consec_loss_gate", close_dt=now - timedelta(minutes=1))
    r = wrap.place_order(
        symbol="TMF", side="BUY", qty=2.0, order_type="MARKET", price=None,
        meta={"ref_price": bid, "stop_price": bid - 50.0, "market_metrics": mm},
    )
    fails += _expect("RISK_CONSEC_LOSS_COOLDOWN", r, "consec_loss_cooldown")

    if fails == 0:
        _clean_seed("daily_max_loss_gate")
        _clean_seed("consec_loss_gate")
        print("[OK] all risk gate smoke tests PASS")
        return 0
    print(f"[FATAL] {fails} test(s) FAIL")
    _clean_seed("daily_max_loss_gate")
    _clean_seed("consec_loss_gate")
    return 2

if __name__ == "__main__":
    raise SystemExit(main())
