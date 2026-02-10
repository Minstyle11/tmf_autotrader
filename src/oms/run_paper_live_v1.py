from __future__ import annotations
# [TMF_AUTO] ensure repo root on sys.path for launchd/script execution
import sys as _sys
from pathlib import Path as _Path
_REPO_ROOT = _Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in _sys.path:
    _sys.path.insert(0, str(_REPO_ROOT))

import sys
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

    # ---- Instrument binding (env-driven; default TMFB6). ----
    # NOTE: instruments.yaml currently defines only group keys (TMFR1/TXFR1/MXFR1),
    # so Paper Live binds to concrete fop_code via env to avoid hardcoding in code.
    fop_code = (os.environ.get("TMF_FOP_CODE", "TMFB6") or "TMFB6").strip()
    bars_symbol = (os.environ.get("TMF_BARS_SYMBOL_FOR_ATR", "") or "").strip() or fop_code
    print(f"[INFO] paper-live fop_code={fop_code} bars_symbol_for_atr={bars_symbol}")

    oms = PaperOMS(db)
    risk = RiskEngineV1(db_path=str(db), cfg=RiskConfigV1(strict_require_market_metrics=1))
    # Safety: strict by default. For after-hours/offline smoke you may set TMF_DEV_ALLOW_STALE_BIDASK=1
    # to allow stale feed ONLY via SystemSafetyEngineV1 override (does NOT disable the staleness guard).
    max_age = int((os.environ.get("TMF_MAX_BIDASK_AGE_SECONDS", "15") or "15").strip())
    allow_synth = (os.environ.get("TMF_ALLOW_SYNTHETIC_BIDASK", "0").strip() == "1")
    safety_cfg = SafetyConfigV1(
        reject_synthetic_bidask=(0 if allow_synth else 1),
        fop_code=fop_code,
        max_bidask_age_seconds=max_age,
        require_recent_bidask=1,
        # Session guard: controlled by env (default off for local smoke; turn on for live/paper-live ops)
        require_session_open=int((os.environ.get("TMF_REQUIRE_SESSION_OPEN", "0") or "0").strip() or "0"),
        session_open_hhmm=(os.environ.get("TMF_SESSION_OPEN_HHMM", "0845") or "0845").strip(),
        session_close_hhmm=(os.environ.get("TMF_SESSION_CLOSE_HHMM", "1345") or "1345").strip(),
        # Optional manual halt dates (YYYY-MM-DD, comma-separated)
        halt_dates_csv=(os.environ.get("TMF_HALT_DATES_CSV", "") or "").strip(),
    )
    if (os.environ.get("TMF_DEV_ALLOW_STALE_BIDASK", "0").strip() == "1"):
        print("[WARN] TMF_DEV_ALLOW_STALE_BIDASK=1 -> stale override requested (NOTE: SystemSafetyEngineV1 HARDGUARD disables this during in-session); intended for after-hours/offline smoke")
    safety = SystemSafetyEngineV1(db_path=str(db), cfg=safety_cfg)
    wrap = PaperOMSRiskSafetyWrapperV1(paper_oms=oms, risk=risk, safety=safety, db_path=str(db))

    # ---- Market snapshot from DB (truthy only; do NOT fabricate market_metrics) ----
    mm = get_market_metrics_from_db(db_path=str(db), fop_code=fop_code, bars_symbol_for_atr=bars_symbol, atr_n=20) or {}

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

    # Expectation depends on offline mode:
    # - allow_stale=0 (strict default): we EXPECT SAFETY_FEED_STALE (and likely cooldown for subsequent attempts)
    # - allow_stale=1 (offline smoke override): we EXPECT RISK_STOP_REQUIRED (risk gate should run)
    allow_stale = (os.environ.get("TMF_DEV_ALLOW_STALE_BIDASK", "0").strip() == "1")    # STRICT logic:
    # - allow_stale=1: we expect SAFETY to pass (stale override) and RISK to reject stop-missing
    # - allow_stale=0: we accept either:
    #     (A) SAFETY_FEED_STALE (if feed is stale), OR
    #     (B) RISK_STOP_REQUIRED (if feed is fresh and risk runs)
    safety_code = (r1.get("safety") or {}).get("code") if isinstance(r1, dict) else None
    risk_code   = (r1.get("risk") or {}).get("code")   if isinstance(r1, dict) else None

    if allow_stale:
        exp1 = (risk_code == "RISK_STOP_REQUIRED")
        expected_case1_code = "RISK_STOP_REQUIRED"
    else:
        exp1 = (safety_code == "SAFETY_FEED_STALE") or (risk_code == "RISK_STOP_REQUIRED")
        expected_case1_code = "SAFETY_FEED_STALE or RISK_STOP_REQUIRED"

    print("[paper-live-smoke] case1_expected_reject_code =", expected_case1_code, "ok=", exp1, "observed_safety=", safety_code, "observed_risk=", risk_code)
    # CASE 2:
    # - allow_stale=1: should PASS place -> fill
    # - allow_stale=0: should be blocked by SAFETY_FEED_STALE and/or SAFETY_COOLDOWN_ACTIVE (both are acceptable strict-mode outcomes)
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

    if isinstance(r2, dict):
        print("[paper-live-smoke] case2_rejected =", r2)
        safety_code = (r2.get("safety") or {}).get("code")
        exp2 = (not allow_stale) and (safety_code in ("SAFETY_FEED_STALE", "SAFETY_COOLDOWN_ACTIVE"))
        print("[paper-live-smoke] smoke_ok =", bool(exp1 and exp2))
        o, f, t = _db_counts(db)
        print("[paper-live-smoke] db_counts orders/fills/trades =", o, f, t)
        print("[paper-live-smoke] last_orders:")
        for row in _last_orders(db, n=8):
            print(row)
        return 0 if (exp1 and exp2) else 1

    print("[paper-live-smoke] case2_pass_place =", f"status={getattr(r2,'status',None)} order_id={getattr(r2,'order_id',None)}")

    # type-narrow: wrapper may return dict(REJECTED) or Order(accepted)
    if isinstance(r2, dict):
        print('[paper-live-smoke] case2_pass_place = REJECTED', r2)
        return 1
    # HARDGUARD: never call PaperOMS.match() on REJECT dict or non-order objects
    def _is_accepted_order(x) -> bool:
        return (not isinstance(x, dict)) and hasattr(x, "order_id") and hasattr(x, "order_type") and hasattr(x, "side")

    if not _is_accepted_order(r2):
        print("[paper-live-smoke] case2_pass_place = NOT_ACCEPTED_ORDER_OBJECT", type(r2), r2)
        return 1

    fills = oms.match(r2, market_price=(bid + 0.5), liquidity_qty=10.0, reason='paper_live_smoke_fill')
    print("[paper-live-smoke] case2_fills =", len(fills))
    exp2 = (len(fills) >= 1)
    print("[paper-live-smoke] smoke_ok =", bool(exp1 and exp2))
    o, f, t = _db_counts(db)
    print("[paper-live-smoke] db_counts orders/fills/trades =", o, f, t)
    print("[paper-live-smoke] last_orders:")
    for row in _last_orders(db, n=8):
        print(row)

    return 0 if (exp1 and exp2) else 1


if __name__ == "__main__":
    sys.exit(main())
