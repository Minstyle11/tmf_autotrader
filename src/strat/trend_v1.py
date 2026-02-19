from __future__ import annotations

import os
from collections import deque
from typing import Any, Deque, Dict, Optional, Tuple

from .strategy_base_v1 import StrategyBaseV1, StrategyContextV1, StrategySignalV1


def _f(x: Any, d: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return float(d)


class TrendStrategyV1(StrategyBaseV1):
    """
    Trend-following breakout (dual-side) with ATR-based stop.
    - Entry: Donchian breakout (close > max(high, N) => BUY; close < min(low, N) => SELL)
    - Stop: entry +/- (atr_mult * ATR)
    - Attribution: reason/confidence/features/tags filled for audit/replay.
    """

    name = "TrendStrategyV1"

    def __init__(
        self,
        *,
        qty: float = 2.0,
        lookback: int = 20,
        atr_n: int = 14,
        atr_mult: float = 2.0,
    ):
        self.qty = float(qty)
        # Auto-patch: required state for force-first + warmup
        self._forced_once = False
        self._force_last_side = None  # last forced side (BUY/SELL)\n        # Auto-patch: required stateful buffers for on_bar warmup
        dq = __import__("collections").deque
        if not hasattr(self, "_highs"):  self._highs  = dq(maxlen=512)
        if not hasattr(self, "_lows"):   self._lows   = dq(maxlen=512)
        if not hasattr(self, "_closes"): self._closes = dq(maxlen=512)
        # Auto-patch: ATR state for warmup/online update
        self._prev_close = None
        self._atr = None
        self._tr_values = []
        if not hasattr(self, "lookback"): self.lookback = 20
        if not hasattr(self, "atr_n"):    self.atr_n    = 20

        self.lookback = int(lookback)
        self.atr_n = int(atr_n)
        self.atr_mult = float(atr_mult)

    @classmethod
    def from_env(cls, *, qty: float = None):
        """Env-driven constructor (keeps runner/spec stable).
        - qty: if None, reads TMF_QTY (default 2.0)
        """
        import os
        if qty is None:
            qty = float((os.environ.get("TMF_QTY", "2.0") or "2.0").strip())
        return cls(qty=qty)

        # rolling windows
        self._highs: Deque[float] = deque(maxlen=max(2, self.lookback))
        self._lows: Deque[float] = deque(maxlen=max(2, self.lookback))
        self._closes: Deque[float] = deque(maxlen=max(3, self.lookback + 2))

        # ATR (Wilder smoothing)
        self._atr: Optional[float] = None
        self._prev_close: Optional[float] = None

        # optional dev helper for deterministic smoke
        self._forced_once = False

    def _update_atr(self, h: float, l: float, c: float) -> Optional[float]:
        if self._prev_close is None:
            tr = h - l
        else:
            tr = max(h - l, abs(h - self._prev_close), abs(l - self._prev_close))

        if self._atr is None:
            # bootstrap with simple mean of first atr_n TRs (approx via incremental)
            # we keep a small buffer by reusing deque of closes/highs/lows: ok for early phase
            self._atr = tr
        else:
            n = max(1, int(self.atr_n))
            self._atr = (self._atr * (n - 1) + tr) / n

        self._prev_close = c
        return self._atr

    def on_bar(self, ctx: StrategyContextV1, bar: Dict[str, Any]) -> Optional[StrategySignalV1]:
        # bar expected keys from runner: o/h/l/c (+ optional)
        h = _f(bar.get("h"))
        l = _f(bar.get("l"))
        c = _f(bar.get("c"))

        self._highs.append(h)
        self._lows.append(l)
        self._closes.append(c)

        atr = self._update_atr(h, l, c)

        # --- DEV ONLY: allow first signal for smoke determinism (kept but not default behavior)
        force_first = str(os.environ.get("TMF_TREND_FORCE_FIRST_SIGNAL", "0")).strip() in ("1", "true", "TRUE", "yes", "YES")
        if force_first and (not self._forced_once) and len(self._closes) >= 2:
            self._forced_once = True
            side = "BUY" if (c >= self._closes[-2]) else "SELL"
            stop_pts = float(os.environ.get("TMF_TREND_FORCE_STOP_PTS", "30"))
            stop_price = (c - stop_pts) if side == "BUY" else (c + stop_pts)
            return StrategySignalV1(
                side=side,
                qty=self.qty,
                order_type="MARKET",
                stop_price=float(stop_price),
                reason=f"trend_v1:dev_force_first({side})",
                confidence=0.51,
                features={"c": c, "prev_c": self._closes[-2], "stop_pts": stop_pts},
                tags={"kind": "trend", "impl": "donchian_atr", "dev_force_first": True},
            )

        # need enough bars for donchian
        if len(self._highs) < self.lookback or len(self._lows) < self.lookback:
            return None

        # Donchian channel excluding current bar is more conservative; here we use last lookback highs/lows including current bar,
        # but breakouts will still require c to exceed recent extremes.
        hh = max(self._highs)
        ll = min(self._lows)

        if atr is None:
            return None
        atr = float(max(0.0, atr))

        # Entry rules
        side: Optional[str] = None
        reason = ""
        if c >= hh and (hh - ll) > 0:
            side = "BUY"
            reason = "trend_v1:donchian_breakout_up"
        elif c <= ll and (hh - ll) > 0:
            side = "SELL"
            reason = "trend_v1:donchian_breakout_down"
        else:
            return None

        # Stop based on ATR multiple
        stop_dist = max(1e-9, self.atr_mult * atr)
        stop_price = (c - stop_dist) if side == "BUY" else (c + stop_dist)

        # confidence: normalized breakout strength vs ATR (capped)
        # (for BUY: (c - mid)/ATR ; for SELL: (mid - c)/ATR)
        mid = 0.5 * (hh + ll)
        strength = abs(c - mid) / (atr + 1e-9)
        conf = max(0.50, min(0.95, 0.50 + 0.05 * strength))

        features: Dict[str, Any] = {
            "c": c,
            "hh": hh,
            "ll": ll,
            "mid": mid,
            "atr": atr,
            "lookback": self.lookback,
            "atr_n": self.atr_n,
            "atr_mult": self.atr_mult,
            "stop_dist": stop_dist,
        }
        tags: Dict[str, Any] = {
            "kind": "trend",
            "impl": "donchian_atr",
            "dual_side": True,
        }

        return StrategySignalV1(
            side=side,  # type: ignore[arg-type]
            qty=self.qty,
            order_type="MARKET",
            stop_price=float(stop_price),
            reason=reason,
            confidence=float(conf),
            features=features,
            tags=tags,
        )


def _main_selftest() -> int:
    # micro self-test to guard syntax/runtime
    s = TrendStrategyV1(qty=2.0, lookback=5, atr_n=3, atr_mult=2.0)
    ctx = StrategyContextV1(now_ts="2026-02-13T00:00:00", symbol="TMFB6")

    bars = [
        {"o": 100, "h": 101, "l": 99, "c": 100},
        {"o": 100, "h": 102, "l": 99, "c": 101},
        {"o": 101, "h": 103, "l": 100, "c": 102},
        {"o": 102, "h": 104, "l": 101, "c": 103},
        {"o": 103, "h": 105, "l": 102, "c": 104},
        {"o": 104, "h": 106, "l": 103, "c": 106},  # breakout-ish
    ]
    got = None
    for b in bars:
        got = s.on_bar(ctx, b)
    # allow None, but if signal appears it must have stop_price
    if got is not None and got.stop_price is None:
        raise AssertionError("signal must carry stop_price")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main_selftest())
