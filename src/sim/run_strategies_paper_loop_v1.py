from __future__ import annotations

import argparse
import os
import sqlite3
import time
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
            "SELECT ts_min, o, h, l, c, v, n_trades, source "
            "FROM bars_1m WHERE symbol=? ORDER BY ts_min DESC LIMIT 1",
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


def _build_market_metrics(*, db_path: Path, fop_code: str, bars_symbol_for_atr: str, atr_n: int, asof_ts: str) -> Dict[str, Any]:
    mm = get_market_metrics_from_db(
        db_path=str(db_path),
        fop_code=fop_code,
        bars_symbol_for_atr=bars_symbol_for_atr,
        atr_n=atr_n,
        asof_ts=asof_ts,
    ) or {}
    # STRICT: do NOT fabricate market_metrics; only include when bid/ask truly present.
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
    if signal.side == "BUY":
        signal.stop_price = ref_price - default_stop_pts
    else:
        signal.stop_price = ref_price + default_stop_pts
    signal.tags = dict(signal.tags or {})
    signal.tags["engine_stop_fallback"] = True
    signal.tags["engine_default_stop_points"] = default_stop_pts
    return signal


def _load_strategies() -> List[Any]:
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


def main() -> int:
    p = argparse.ArgumentParser(description="TMF AutoTrader strategy runner (paper, loop) v1")
    p.add_argument("--db", default=os.environ.get("TMF_DB_PATH", "runtime/data/tmf_autotrader_v1.sqlite3"))
    p.add_argument("--symbol", default=os.environ.get("TMF_SYMBOL", "TMF"))
    p.add_argument("--max-seconds", type=float, default=float((os.environ.get("TMF_MAX_SECONDS","0") or "0").strip()),
                  help="auto-exit after N seconds (0=run forever); env TMF_MAX_SECONDS")
    args = p.parse_args()
    t0 = time.time()

    db = Path(args.db)
    db.parent.mkdir(parents=True, exist_ok=True)
    init_db(db)

    # Instrument binding (env-driven)
    fop_code = (os.environ.get("TMF_FOP_CODE", "TMFB6") or "TMFB6").strip()
    bars_symbol = (os.environ.get("TMF_BARS_SYMBOL_FOR_ATR", "") or "").strip() or fop_code
    atr_n = int((os.environ.get("TMF_ATR_N", "20") or "20").strip())

    # Engines
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

    # Loop settings
    poll_sec = float((os.environ.get("TMF_POLL_SECONDS", "0.5") or "0.5").strip())
    one_order_per_bar = int((os.environ.get("TMF_ONE_ORDER_PER_BAR", "1") or "1").strip()) == 1

    strats = _load_strategies()
    print(f"[BOOT] symbol={args.symbol} fop_code={fop_code} max_age={max_age}s poll={poll_sec}s "
          f"one_order_per_bar={int(one_order_per_bar)} strategies={','.join([getattr(s,'name','?') for s in strats])}")

    last_bar_ts = None

    # --- controlled exit for smoke/regression (0 means run forever) ---
    max_loop_seconds = float((os.environ.get("TMF_MAX_LOOP_SECONDS", "0") or "0").strip() or "0")
    max_loop_bars = int((os.environ.get("TMF_MAX_LOOP_BARS", "0") or "0").strip() or "0")
    t_start = time.time()
    bars_seen = 0

    while True:
        if float(getattr(args,'max_seconds',0) or 0) > 0 and (time.time() - t0) >= float(args.max_seconds):
            print(f"[EXIT] reached max_seconds={args.max_seconds}")
            return 0

        bar = _fetch_last_bar_1m(db, fop_code)
        if not bar:
            time.sleep(max(0.2, poll_sec))
            continue

        ts_min = str(bar["ts_min"])
        if last_bar_ts == ts_min:
            time.sleep(max(0.2, poll_sec))
            continue

        last_bar_ts = ts_min

        bars_seen += 1
        if max_loop_seconds > 0 and (time.time() - t_start) >= max_loop_seconds:
            print(f"[EXIT] max_loop_seconds reached: {max_loop_seconds}")
            break
        if max_loop_bars > 0 and bars_seen > max_loop_bars:
            print(f"[EXIT] max_loop_bars reached: {max_loop_bars}")
            break
        ref_price = float(bar["c"])

        # Pull market_metrics fresh every new bar (must reflect latest NON-synthetic bidask)
        mm = _build_market_metrics(db_path=db, fop_code=fop_code, bars_symbol_for_atr=bars_symbol, atr_n=atr_n, asof_ts=ts_min)
        if not mm:
            print(f"[SKIP] bar_ts={ts_min} no market_metrics(bid/ask) in DB yet")
            time.sleep(max(0.2, poll_sec))
            continue

        ctx = StrategyContextV1(now_ts=ts_min, symbol=args.symbol, state={})
        print(f"[BAR] ts={ts_min} c={ref_price} spread={mm.get('spread_points')} liq={mm.get('liquidity_score')} bidask_ts={(mm.get('source') or {}).get('bidask_ts')} bidask_id={(mm.get('source') or {}).get('bidask_event_id')}")

        placed = False
        for s in strats:
            sig = s.on_bar_1m(ctx, bar)
            if sig is None:
                continue

            sig = _ensure_stop(sig, ref_price=ref_price)
            meta = sig.to_order_meta(
                strat_name=getattr(s, "name", "unknown"),
                strat_version=getattr(s, "version", "v?"),
                ref_price=ref_price,
            )
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

            # --- PAPER AUTOFILL (v1) ---
            # In paper mode, accepted orders must be matched to generate fills/trades.
            # Default: auto-match MARKET orders immediately using conservative bid/ask.
            try:
                auto_match = (os.environ.get("TMF_PAPER_AUTOMATCH", "1").strip() == "1")
                liq_qty = float(os.environ.get("TMF_PAPER_MATCH_LIQ_QTY", "10.0") or "10.0")
                is_order_obj = hasattr(r, "order_id") and hasattr(r, "order_type") and hasattr(r, "side")
                if auto_match and is_order_obj:
                    bid = float((mm.get("bid") or 0.0))
                    ask = float((mm.get("ask") or 0.0))
                    px = ask if str(getattr(r, "side", "")).upper() == "BUY" else bid
                    if px > 0:
                        fills = wrap.paper_oms.match(r, market_price=float(px), liquidity_qty=liq_qty, reason="paper_loop_autofill")
                        print(f"[MATCH] order_id={getattr(r,'order_id',None)} side={getattr(r,'side',None)} market_price={px} fills={len(fills)}")
            except Exception as _e:
                print(f"[WARN] paper_autofill failed: {_e}")
            placed = True
            if one_order_per_bar:
                break

        if not placed:
            print("[INFO] no signal")

        time.sleep(max(0.2, poll_sec))

    # unreachable
    # return 0


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
    raise SystemExit(main())
