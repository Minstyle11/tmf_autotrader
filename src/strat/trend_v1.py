from __future__ import annotations
import os
from typing import Any, Dict, Optional

from .strategy_base_v1 import StrategyBaseV1, StrategyContextV1, StrategySignalV1


class TrendStrategyV1(StrategyBaseV1):
    name = "TrendStrategyV1"
    version = "v1"

    def __init__(self, *, qty: float = 2.0):
        self.qty = float(qty)
        self._last_close: Optional[float] = None

    def on_bar_1m(self, ctx: StrategyContextV1, bar: Dict[str, Any]) -> Optional[StrategySignalV1]:
        c = float(bar.get("c")) if bar.get("c") is not None else None
        if c is None:
            return None

        thr_pts = float((os.environ.get("TMF_TREND_THRESHOLD_POINTS", "10") or "10").strip())
        stop_pts = float((os.environ.get("TMF_TREND_STOP_POINTS", "50") or "50").strip())

        # TEST HOOK: force a first signal to validate end-to-end order wiring.
        if self._last_close is None and (os.environ.get("TMF_STRAT_FORCE_FIRST_SIGNAL", "0").strip() == "1"):
            side = (os.environ.get("TMF_STRAT_FORCE_FIRST_SIDE", "BUY") or "BUY").strip().upper()
            if side not in ("BUY", "SELL"):
                side = "BUY"
            stop_price = (c - stop_pts) if side == "BUY" else (c + stop_pts)
            sig = StrategySignalV1(
                side=side,
                qty=self.qty,
                order_type="MARKET",
                price=None,
                stop_price=stop_price,
                reason=f"trend_skeleton: force_first_signal({side})",
                confidence=0.51,
                features={"c": c, "last_close": self._last_close, "thr_pts": thr_pts, "stop_pts": stop_pts},
                tags={"kind": "trend", "impl": "skeleton", "force_first_signal": True, "stop_points": stop_pts, "threshold_points": thr_pts},
            )
            self._last_close = c
            return sig

        if self._last_close is None:
            self._last_close = c
            return None

        d = c - float(self._last_close)

        # Dual-side skeleton: breakout continuation
        if d >= thr_pts:
            side = "BUY"
            stop_price = c - stop_pts
            reason = "trend_skeleton: breakout_up"
            conf = 0.53
        elif d <= -thr_pts:
            side = "SELL"
            stop_price = c + stop_pts
            reason = "trend_skeleton: breakout_down"
            conf = 0.53
        else:
            self._last_close = c
            return None

        sig = StrategySignalV1(
            side=side,
            qty=self.qty,
            order_type="MARKET",
            price=None,
            stop_price=stop_price,
            reason=reason,
            confidence=conf,
            features={"c": c, "last_close": self._last_close, "delta": d, "thr_pts": thr_pts, "stop_pts": stop_pts},
            tags={"kind": "trend", "impl": "skeleton", "stop_points": stop_pts, "threshold_points": thr_pts},
        )
        self._last_close = c
        return sig
