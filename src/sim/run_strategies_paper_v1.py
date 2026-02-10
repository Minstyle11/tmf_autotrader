from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional, List

from src.data.store_sqlite_v1 import init_db
from src.oms.paper_oms_v1 import PaperOMS
from src.oms.paper_oms_risk_safety_wrapper_v1 import PaperOMSRiskSafetyWrapperV1
from src.risk.risk_engine_v1 import RiskEngineV1, RiskConfigV1
from src.safety.system_safety_v1 import SystemSafetyEngineV1, SafetyConfigV1
from src.market.market_metrics_from_db_v1 import get_market_metrics_from_db

from src.strat.trend_v1 import TrendStrategyV1
from src.strat.mean_reversion_v1 import MeanReversionStrategyV1
from src.strat.strategy_base_v1 import StrategyContextV1, StrategySignalV1

def _vol_regime_from_atr(atr_points: float) -> str:
    """
    Minimal volatility regime classifier (v1).
    ATR is in "points" of the instrument price scale (same unit as bid/ask).
    Thresholds are env-tunable to support rapid ops calibration.
    """
    import os
    low_max = float((os.environ.get("TMF_VOL_REGIME_LOW_MAX_ATR", "30") or "30").strip())
    mid_max = float((os.environ.get("TMF_VOL_REGIME_MID_MAX_ATR", "60") or "60").strip())
    high_max = float((os.environ.get("TMF_VOL_REGIME_HIGH_MAX_ATR", "90") or "90").strip())
    x = float(atr_points)
    if x <= low_max:
        return "LOW"
    if x <= mid_max:
        return "MID"
    if x <= high_max:
        return "HIGH"
    return "EXTREME"


def _apply_vol_confidence(meta: dict, mm: dict) -> dict:
    """
    v18 task: signal_confidence must be modulated by vol_regime.
    We keep raw confidence for audit, and write adjusted confidence used by the engine.
    """
    import os
    atr = mm.get("atr_points")
    if atr is None:
        return meta
    try:
        regime = _vol_regime_from_atr(float(atr))
    except Exception:
        return meta

    # factors: conservative by default (high vol -> lower confidence)
    f_low  = float((os.environ.get("TMF_CONF_FACTOR_LOW", "1.05") or "1.05").strip())
    f_mid  = float((os.environ.get("TMF_CONF_FACTOR_MID", "1.00") or "1.00").strip())
    f_high = float((os.environ.get("TMF_CONF_FACTOR_HIGH", "0.80") or "0.80").strip())
    f_ext  = float((os.environ.get("TMF_CONF_FACTOR_EXTREME", "0.60") or "0.60").strip())
    factor = {"LOW": f_low, "MID": f_mid, "HIGH": f_high, "EXTREME": f_ext}.get(regime, f_mid)

    meta = dict(meta or {})
    meta["vol_regime"] = regime

    strat = meta.get("strat") if isinstance(meta.get("strat"), dict) else {}
    raw = strat.get("confidence")
    if raw is None:
        raw = meta.get("signal_confidence")
    if raw is None:
        return meta

    try:
        raw_f = float(raw)
    except Exception:
        return meta

    adj = max(0.0, min(1.0, raw_f * factor))
    meta["signal_confidence_raw"] = raw_f
    meta["signal_confidence"] = adj

    strat = dict(strat)
    strat.setdefault("confidence_raw", raw_f)
    strat["confidence"] = adj
    meta["strat"] = strat
    return meta




def _fetch_last_bar_1m(db_path: Path, symbol: str) -> Optional[Dict[str, Any]]:
    con = sqlite3.connect(str(db_path))
    try:
        row = con.execute(
            "SELECT ts_min, o, h, l, c, v, n_trades, source FROM bars_1m WHERE symbol=? ORDER BY ts_min DESC LIMIT 1",
            (symbol,),
        ).fetchone()
        if not row:
            return None
        ts_min, o, h, l, c, v, n_trades, source = row
        return {
            "ts_min": ts_min,
            "o": float(o),
            "h": float(h),
            "l": float(l),
            "c": float(c),
            "v": float(v),
            "n_trades": int(n_trades),
            "source": source,
        }
    finally:
        con.close()


def _build_market_metrics(*, db_path: Path, fop_code: str, bars_symbol_for_atr: str, atr_n: int) -> Dict[str, Any]:
    mm = get_market_metrics_from_db(db_path=str(db_path), fop_code=fop_code, bars_symbol_for_atr=bars_symbol_for_atr, atr_n=atr_n) or {}
    # IMPORTANT: do NOT fabricate market_metrics; only include when bid/ask truly present.
    if mm.get("bid") is None or mm.get("ask") is None:
        return {}
    bid = float(mm["bid"])
    ask = float(mm["ask"])
    return {
        "bid": bid,
        "ask": ask,
        "spread_points": float(mm.get("spread_points", ask - bid)),
        "atr_points": (None if mm.get("atr_points") is None else float(mm.get("atr_points"))),
        "liquidity_score": float(mm.get("liquidity_score", 0.0)),
        "source": (mm.get("source") or {}),
    }


def _ensure_stop(signal: StrategySignalV1, *, ref_price: float) -> StrategySignalV1:
    # Keep RiskEngine strict; strategy should provide stop when it can.
    # Engine fallback is allowed for skeleton stage to keep flow testable, but is clearly tagged.
    if signal.stop_price is not None:
        return signal
    default_stop_pts = float((os.environ.get("TMF_ENGINE_DEFAULT_STOP_POINTS", "50") or "50").strip())
    # BUY: stop below; SELL: stop above
    if signal.side == "BUY":
        signal.stop_price = ref_price - default_stop_pts
    else:
        signal.stop_price = ref_price + default_stop_pts
    signal.tags = dict(signal.tags or {})
    signal.tags["engine_stop_fallback"] = True
    signal.tags["engine_default_stop_points"] = default_stop_pts
    return signal


def _load_strategies() -> List[Any]:
    # Env-driven list; default run both skeletons.
    spec = (os.environ.get("TMF_STRATEGIES", "trend,mean_reversion") or "trend,mean_reversion").strip()
    keys = [s.strip().lower() for s in spec.split(",") if s.strip()]
    out: List[Any] = []
    for k in keys:
        if k in ("trend", "trend_v1"):
            out.append(TrendStrategyV1(qty=float(os.environ.get("TMF_QTY", "2.0"))))
        elif k in ("mr", "mean_reversion", "mean_reversion_v1"):
            out.append(MeanReversionStrategyV1(qty=float(os.environ.get("TMF_QTY", "2.0"))))
        else:
            print(f"[WARN] unknown strategy key: {k} (skip)")
    return out


def main():
    p = argparse.ArgumentParser(description="TMF AutoTrader strategy runner (paper) v1")
    p.add_argument("--db", default=os.environ.get("TMF_DB_PATH", "runtime/data/tmf_autotrader_v1.sqlite3"))
    p.add_argument("--symbol", default=os.environ.get("TMF_SYMBOL", "TMF"))
    args = p.parse_args()

    db = Path(args.db)
    db.parent.mkdir(parents=True, exist_ok=True)
    init_db(db)

    # Instrument binding (env-driven)
    fop_code = (os.environ.get("TMF_FOP_CODE", "TMFB6") or "TMFB6").strip()
    bars_symbol = (os.environ.get("TMF_BARS_SYMBOL_FOR_ATR", "") or "").strip() or fop_code
    atr_n = int((os.environ.get("TMF_ATR_N", "20") or "20").strip())

    # OMS + engines
    oms = PaperOMS(db)
    risk = RiskEngineV1(db_path=str(db), cfg=RiskConfigV1(strict_require_market_metrics=1))
    max_age = int((os.environ.get("TMF_MAX_BIDASK_AGE_SECONDS", "15") or "15").strip())
    safety_cfg = SafetyConfigV1(
        fop_code=fop_code,
        max_bidask_age_seconds=max_age,
        require_recent_bidask=1,
        require_session_open=int((os.environ.get("TMF_REQUIRE_SESSION_OPEN", "0") or "0").strip() or "0"),
        session_open_hhmm=(os.environ.get("TMF_SESSION_OPEN_HHMM", "0845") or "0845").strip(),
        session_close_hhmm=(os.environ.get("TMF_SESSION_CLOSE_HHMM", "1345") or "1345").strip(),
        halt_dates_csv=(os.environ.get("TMF_HALT_DATES_CSV", "") or "").strip(),
    )
    safety = SystemSafetyEngineV1(db_path=str(db), cfg=safety_cfg)
    wrap = PaperOMSRiskSafetyWrapperV1(paper_oms=oms, risk=risk, safety=safety, db_path=str(db))

    # Data: last bar (truthy)
    bar = _fetch_last_bar_1m(db, bars_symbol_for_atr)
    if not bar:
        print(f"[SKIP] no bars_1m for symbol={args.symbol}")
        return
    ref_price = float(bar["c"])

    mm = _build_market_metrics(db_path=db, fop_code=fop_code, bars_symbol_for_atr=bars_symbol, atr_n=atr_n)
    if not mm:
        print("[REJECT] market_metrics missing bid/ask from DB (strict_require_market_metrics=1).")
        return

    ctx = StrategyContextV1(now_ts=str(bar["ts_min"]), symbol=args.symbol, state={})
    strats = _load_strategies()
    print(f"[INFO] strategies={','.join([getattr(s,'name','?') for s in strats])} bar_ts={bar['ts_min']} c={ref_price}")
    for s in strats:
        sig = s.on_bar_1m(ctx, bar)
        if sig is None:
            continue

        sig = _ensure_stop(sig, ref_price=ref_price)
        meta = sig.to_order_meta(strat_name=getattr(s, "name", "unknown"), strat_version=getattr(s, "version", "v?"), ref_price=ref_price)
        meta["market_metrics"] = mm


        meta = _apply_vol_confidence(meta, mm)
        print(f"[SIGNAL] strat={getattr(s,'name','?')} side={sig.side} qty={sig.qty} stop={sig.stop_price} reason={sig.reason}")
        r = wrap.place_order(
            symbol=args.symbol,
            side=sig.side,
            qty=float(sig.qty),
            order_type=str(sig.order_type),
            price=(None if sig.price is None else float(sig.price)),
            meta=meta,
        )
        print("[ORDER]", r)
        # For v1 runner: one order per bar to keep behavior deterministic
        return

    print("[INFO] no signal")


if __name__ == "__main__":
    main()
