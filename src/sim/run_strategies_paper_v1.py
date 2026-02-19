from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional, List

from src.ops.learning.governance_v1 import env_mode, LearningMode, shadow_log_intent, enforce_promote_canary
from src.ops.learning.drift_detector_v1 import run_drift_detector_v1


def _learning_governance_apply(*, strat_name: str, side: str, qty: float, meta: dict) -> tuple[bool, str]:
    """
    Returns (allow_place, reason).
    - FROZEN: allow normal paper trading (no adaptive modifications)
    - SHADOW: DO NOT place; log intent + reason
    - PROMOTE: allow but must pass canary bounds; otherwise block
    """
    if LEARNING_MODE == LearningMode.SHADOW:
        shadow_log_intent(intent={
            "kind": "shadow_intent",
            "strat": strat_name,
            "side": side,
            "qty": qty,
            "meta": meta,
            "reason": "LEARNING_MODE_SHADOW",
        })
        return (False, "LEARNING_MODE_SHADOW")
    if LEARNING_MODE == LearningMode.PROMOTE:
        why = enforce_promote_canary(strat_name=strat_name, qty=qty, side=side)
        if why:
            shadow_log_intent(intent={
                "kind": "promote_blocked",
                "strat": strat_name,
                "side": side,
                "qty": qty,
                "meta": meta,
                "reason": why,
            })
            return (False, why)
    return (True, "OK")


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
            out.append(TrendStrategyV1.from_env(qty=float(__import__("os").environ.get("TMF_QTY","2.0"))))
        elif k in ("mr", "mean_reversion", "mean_reversion_v1"):
            out.append(MeanReversionStrategyV1.from_env())
        else:
            print(f"[WARN] unknown strategy key: {k} (skip)")
    # Back-compat: allow class-name filter via TMF_STRAT_ONLY
    only = str(os.environ.get("TMF_STRAT_ONLY", "")).strip()
    if only:
        out = [st for st in out if st.__class__.__name__ == only]
        print("[INFO] TMF_STRAT_ONLY=%s -> strats=%s" % (only, [st.__class__.__name__ for st in out]))
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

    # Data: warmup recent bars so stateful strategies (Donchian/ATR) can produce signals
    strats = _load_strategies()
    if not strats:
        print("[INFO] no strategies enabled; exit")
        return 0

    warm_base = 0
    for st in strats:
        warm_base = max(warm_base, int(getattr(st, "lookback", 20)), int(getattr(st, "atr_n", 14)))
    warm_n = int(warm_base + 2)

    bars = _fetch_recent_bars_1m(db, bars_symbol, warm_n)
    if not bars:
        print("[INFO] no bars_1m rows for symbol; exit")
        return 0

    last_bar = bars[-1]
    if (not last_bar) or (last_bar.get("c") is None):
        print(f"[SKIP] invalid last bar for symbol={args.symbol}")
        return 0

    ref_price = float(last_bar["c"])

    mm = _build_market_metrics(db_path=db, fop_code=fop_code, bars_symbol_for_atr=bars_symbol, atr_n=atr_n)
    if not mm:
        print("[REJECT] market_metrics missing bid/ask from DB (strict_require_market_metrics=1).")
        return 0

    strat_names = ",".join([getattr(x, "name", x.__class__.__name__) for x in strats])
    print(f"[INFO] strats={strat_names} warm_n={warm_n} last_ts={last_bar.get('ts_min')} c={ref_price}")

    # Warmup: feed historical bars (exclude last) to build indicator state
    # --- PATCH: avoid consuming force-first during warmup ---
    import os as _os  # _FORCE_FIRST_RESTORE
    _ff_key = "TMF_TREND_FORCE_FIRST_SIGNAL"
    _ff_prev = _os.environ.get(_ff_key)
    if _ff_prev is not None:
        _os.environ[_ff_key] = "0"

    for b in bars[:-1]:
        ctx_w = StrategyContextV1(now_ts=str(b.get("ts_min")), symbol=args.symbol, state={})
        for st in strats:
            try:
                fn = getattr(st, "on_bar", None) or getattr(st, "on_bar_1m", None)
                if fn:
                    fn(ctx_w, b)
            except Exception as ex:
                sn = getattr(st, "name", st.__class__.__name__)
                print(f"[WARN] warmup error strat={sn} ts={b.get('ts_min')} ex={ex}")

    # --- PATCH: restore force-first for decision bar ---
    if _ff_prev is not None:
        _os.environ[_ff_key] = _ff_prev

    # Decision: evaluate on the last bar (one order per run)
    ctx = StrategyContextV1(now_ts=str(last_bar.get("ts_min")), symbol=args.symbol, state={})
    for st in strats:
        fn = getattr(st, "on_bar", None) or getattr(st, "on_bar_1m", None)
        if not fn:
            continue
        sig = fn(ctx, last_bar)
        if sig is None:
            continue

        sig = _ensure_stop(sig, ref_price=ref_price)
        meta = sig.to_order_meta(
            strat_name=getattr(st, "name", st.__class__.__name__),
            strat_version=getattr(st, "version", "v?"),
            ref_price=ref_price,
            now_ts=str(ctx.now_ts),
            symbol=str(args.symbol),
        )
        meta["market_metrics"] = mm
        meta = _apply_vol_confidence(meta, mm)

        sn = getattr(st, "name", st.__class__.__name__)
        print(f"[SIGNAL] strat={sn} side={sig.side} qty={sig.qty} stop={sig.stop_price} reason={sig.reason}")
        r = wrap.place_order(
            symbol=args.symbol,
            side=sig.side,
            qty=float(sig.qty),
            order_type=str(sig.order_type),
            price=(None if sig.price is None else float(sig.price)),
            meta=meta,
        )
        print("[ORDER]", r)
        return 0

    print("[INFO] no signal")
    return 0
def _fetch_recent_bars_1m(db: str, symbol: str, n: int):
    """Return recent 1m bars ascending by ts_min. Best-effort compatible with existing schema."""
    import sqlite3
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    try:
        # Expect bars_1m(ts_min, symbol, o,h,l,c,v, n_trades, source) (or superset)
        rows = con.execute(
            """
            SELECT ts_min, o, h, l, c, v, COALESCE(n_trades, 0) AS n_trades, COALESCE(source, '') AS source
            FROM bars_1m
            WHERE symbol = ?
            ORDER BY ts_min DESC
            LIMIT ?
            """,
            (symbol, int(max(0, n))),
        ).fetchall()
        rows = list(reversed(rows))
        out = []
        for r in rows:
            out.append({
                "ts_min": r["ts_min"],
                "o": float(r["o"]) if r["o"] is not None else None,
                "h": float(r["h"]) if r["h"] is not None else None,
                "l": float(r["l"]) if r["l"] is not None else None,
                "c": float(r["c"]) if r["c"] is not None else None,
                "v": float(r["v"]) if r["v"] is not None else None,
                "n_trades": int(r["n_trades"]) if r["n_trades"] is not None else 0,
                "source": r["source"],
            })
        return out
    finally:
        con.close()


# --- Learning Governance Hook (v18.1) ---
LEARNING_MODE = env_mode(LearningMode.FROZEN)

# Fail-safe: drift detector runs at runner start; any trigger freezes governance
try:
    _dr = run_drift_detector_v1()
    if not _dr.ok:
        # drift detector already froze governance state; keep runner conservative
        LEARNING_MODE = LearningMode.FROZEN
except Exception:
    # ultra-conservative: on detector failure, freeze
    LEARNING_MODE = LearningMode.FROZEN


if __name__ == "__main__":
    main()
