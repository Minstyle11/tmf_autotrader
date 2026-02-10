from __future__ import annotations
import os
from typing import Any, Dict, Optional

from .strategy_base_v1 import StrategyBaseV1, StrategyContextV1, StrategySignalV1


class MeanReversionStrategyV1(StrategyBaseV1):
    name = "MeanReversionStrategyV1"
    version = "v1"

    def __init__(self, *, qty: float = 2.0):
        self.qty = float(qty)
        self._last_close: Optional[float] = None

    def on_bar_1m(self, ctx: StrategyContextV1, bar: Dict[str, Any]) -> Optional[StrategySignalV1]:
        # Skeleton: replace with z-score / band logic later.
        c = float(bar.get("c")) if bar.get("c") is not None else None
        if c is None:
            return None

        entry_pts = float((os.environ.get("TMF_MR_ENTRY_POINTS", "10") or "10").strip())
        stop_pts = float((os.environ.get("TMF_MR_STOP_POINTS", "50") or "50").strip())

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
                reason=f"mean_reversion_skeleton: force_first_signal({side})",
                confidence=0.51,
                features={"c": c, "last_close": self._last_close, "entry_pts": entry_pts, "stop_pts": stop_pts},
                tags={"kind": "mean_reversion", "impl": "skeleton", "force_first_signal": True, "stop_points": stop_pts, "entry_points": entry_pts},
            )
            self._last_close = c
            return sig

        if self._last_close is None:
            self._last_close = c
            return None

        last = float(self._last_close)

        # Dual-side skeleton:
        # - If price drops enough vs last_close => BUY for bounce
        # - If price rises enough vs last_close => SELL(short) for pullback
        if c <= last - entry_pts:
            side = "BUY"
            stop_price = c - stop_pts
            reason = "mr_skeleton: c<=last-entry"
            conf = 0.52
        elif c >= last + entry_pts:
            side = "SELL"
            stop_price = c + stop_pts
            reason = "mr_skeleton: c>=last+entry"
            conf = 0.52
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
            features={"c": c, "last_close": last, "entry_pts": entry_pts, "stop_pts": stop_pts},
            tags={"kind": "mean_reversion", "impl": "skeleton", "stop_points": stop_pts, "entry_points": entry_pts},
        )
        self._last_close = c
        return sig
