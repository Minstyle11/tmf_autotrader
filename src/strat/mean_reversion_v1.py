"""
Mean Reversion Strategy v1 (TMF AutoTrader)

Design goals (v18-aligned):
- Dual-side signals (BUY/SELL)
- Stop-required compatible: always provide stop_price in signal
- Attribution/audit friendly: stable tags/features for meta_json
- Deterministic dev testing: TMF_MR_FORCE_FIRST_SIGNAL=1 alternates side
"""

from __future__ import annotations

import os
import math
from dataclasses import dataclass
from typing import Any, Dict, Optional, List

from .strategy_base_v1 import StrategyBaseV1, StrategyContextV1, StrategySignalV1


def _env_float(name: str, default: float) -> float:
    try:
        return float(str(os.environ.get(name, str(default))).strip())
    except Exception:
        return float(default)


def _env_int(name: str, default: int) -> int:
    try:
        return int(float(str(os.environ.get(name, str(default))).strip()))
    except Exception:
        return int(default)


def _env_bool(name: str, default: bool = False) -> bool:
    v = os.environ.get(name, None)
    if v is None:
        return default
    return str(v).strip().lower() in ("1", "true", "yes", "y", "on")


def _stdev(xs: List[float]) -> float:
    # population stdev (stable for small n)
    n = len(xs)
    if n <= 1:
        return 0.0
    mu = sum(xs) / n
    var = sum((x - mu) ** 2 for x in xs) / n
    return math.sqrt(var)


@dataclass
class MeanReversionConfigV1:
    lookback_n: int = 40           # window for mean/std
    entry_z: float = 2.0           # enter when |z| >= entry_z
    stop_pts: float = 30.0         # stop distance in points
    qty: float = 2.0               # order qty
    cooldown_bars: int = 5         # throttle repeated signals
    force_first: bool = False      # dev: always emit a signal
    force_alt: bool = True         # dev: alternate BUY/SELL when force_first


class MeanReversionStrategyV1(StrategyBaseV1):
    name = "MeanReversionStrategyV1"
    version = "v1"

    def __init__(self, cfg: Optional[MeanReversionConfigV1] = None):
        self.cfg = cfg or MeanReversionConfigV1()
        # Runner warmup uses getattr(st, "lookback", ...) / getattr(st, "atr_n", ...)
        # Expose stable attrs so warm_n is correct for MR (v18 audit/replay consistency)
        self.lookback = int(getattr(self.cfg, "lookback_n", 40))
        self.atr_n = 0
    @classmethod
    def from_env(cls) -> "MeanReversionStrategyV1":
        cfg = MeanReversionConfigV1(
            lookback_n=_env_int("TMF_MR_LOOKBACK_N", 40),
            entry_z=_env_float("TMF_MR_ENTRY_Z", 2.0),
            stop_pts=_env_float("TMF_MR_STOP_PTS", 30.0),
            qty=_env_float("TMF_MR_QTY", 2.0),
            cooldown_bars=_env_int("TMF_MR_COOLDOWN_BARS", 5),
            force_first=_env_bool("TMF_MR_FORCE_FIRST_SIGNAL", False),
            force_alt=_env_bool("TMF_MR_FORCE_ALT_SIDE", True),
        )
        return cls(cfg=cfg)

    def _cooldown_ok(self, ctx: StrategyContextV1, bars: List[Dict[str, Any]]) -> bool:
        # bar-index based cooldown (robust even if now_ts is old in replay)
        k = f"{self.name}.last_signal_bar_idx"
        last_idx = ctx.state.get(k, None)
        if last_idx is None:
            return True
        try:
            last_idx = int(last_idx)
        except Exception:
            return True
        cur_idx = len(bars) - 1
        return (cur_idx - last_idx) >= int(self.cfg.cooldown_bars)

    def _set_last_signal(self, ctx: StrategyContextV1, bars: List[Dict[str, Any]]) -> None:
        ctx.state[f"{self.name}.last_signal_bar_idx"] = len(bars) - 1

    def on_bar(self, ctx, bar):
        """Runner entrypoint (paper): feed 1m bars into MR window, then delegate to generate_signal(ctx=..., bars=[...])."""
        # Lazy init rolling window
        if not hasattr(self, "_bars"):
            from collections import deque
            maxlen = int(getattr(self, "lookback", 40)) + 5
            self._bars = deque(maxlen=maxlen)

        # Normalize minimal bar schema
        b = dict(bar or {})
        # runner uses dict rows from sqlite, keys: ts_min/o/h/l/c/v...
        # generate_signal expects c at least.
        if "c" not in b:
            return None

        self._bars.append(b)

        # Warmup guard: need lookback+2 closes to compute prev/mean/threshold
        need = int(getattr(self, "lookback", 40)) + 2
        if len(self._bars) < need:
            return None

        try:
            return self.generate_signal(ctx=ctx, bars=list(self._bars))
        except TypeError:
            # Backward compat if signature differs
            return self.generate_signal(ctx=ctx, bars=list(self._bars))



    def generate_signal(self, *, ctx: StrategyContextV1, bars: List[Dict[str, Any]]) -> Optional[StrategySignalV1]:
        n = int(self.cfg.lookback_n)
        if len(bars) < n + 1:
            return None
        # Dev harness: deterministic first signal for end-to-end pipeline tests
        if bool(getattr(self.cfg, "force_first", False)):
            last_side = str(ctx.state.get(f"{self.name}.force_last_side", ""))
            if bool(getattr(self.cfg, "force_alt", True)):
                side = "SELL" if last_side == "BUY" else "BUY"
            else:
                side = "BUY"
            c0 = float(bars[-1].get("c", bars[-1].get("close")))
            stop_pts = float(getattr(self.cfg, "stop_pts", 30.0))
            stop_price = (c0 - stop_pts) if side == "BUY" else (c0 + stop_pts)
            ctx.state[f"{self.name}.force_last_side"] = side
            self._set_last_signal(ctx, bars)
            reason = f"mean_reversion_v1:dev_force_first({side})"
            return StrategySignalV1(
                side=side,
                qty=float(getattr(self.cfg, "qty", 2.0)),
                order_type="MARKET",
                price=None,
                stop_price=float(stop_price),
                reason=reason,
                confidence=0.51,
                confidence_raw=0.51,
                features={"c": c0, "stop_pts": stop_pts},
                tags={"kind": "mean_reversion", "impl": "zscore", "dev_force_first": True},
            )

        # Cooldown gate (bar-index based, replay-safe)
        if (not self.cfg.force_first) and (not self._cooldown_ok(ctx, bars)):
            return None


        # Extract closes (prefer c then close)
        closes: List[float] = []
        for b in bars[-n:]:
            c = b.get("c", b.get("close", None))
            if c is None:
                return None
            closes.append(float(c))

        c = closes[-1]
        prev_c = closes[-2]
        mu = sum(closes) / len(closes)
        sd = _stdev(closes)

        if sd <= 0:
            return None

        z = (c - mu) / sd

        # Cooldown throttle unless dev force_first
        if (not self.cfg.force_first) and (not self._cooldown_ok(ctx, bars)):
            return None

        side: Optional[str] = None
        reason: str = ""
        dev_force = False

        if self.cfg.force_first:
            dev_force = True
            if self.cfg.force_alt:
                last_side = ctx.state.get(f"{self.name}.last_force_side", "SELL")
                side = "BUY" if last_side == "SELL" else "SELL"
                ctx.state[f"{self.name}.last_force_side"] = side
            else:
                side = "BUY"
            reason = f"meanrev_v1:dev_force_first({side})"
        else:
            if z <= -abs(self.cfg.entry_z):
                side = "BUY"
                reason = f"meanrev_v1:z_le(-{self.cfg.entry_z})"
            elif z >= abs(self.cfg.entry_z):
                side = "SELL"
                reason = f"meanrev_v1:z_ge(+{self.cfg.entry_z})"
            else:
                return None

        # Stop required: set stop_price away from ref price by stop_pts
        stop_pts = float(self.cfg.stop_pts)
        stop_price = (c - stop_pts) if side == "BUY" else (c + stop_pts)

        # Confidence: monotonic in |z|, soft capped
        z_abs = abs(z)
        conf_raw = min(0.99, max(0.05, z_abs / (abs(self.cfg.entry_z) * 2.0)))
        # Slightly reward mean distance
        conf = min(0.99, conf_raw * 1.03)

        sig = StrategySignalV1(
            side=side,
            qty=float(self.cfg.qty),
            order_type="MARKET",
            price=None,
            stop_price=float(stop_price),
            reason=reason,
            confidence=float(conf),
            confidence_raw=float(conf_raw),
            features={
                "c": float(c),
                "prev_c": float(prev_c),
                "mean": float(mu),
                "stdev": float(sd),
                "z": float(z),
                "entry_z": float(self.cfg.entry_z),
                "stop_pts": float(stop_pts),
                "lookback_n": int(n),
            },
            tags={
                "kind": "mean_reversion",
                "impl": "bollinger_zscore",
                "dev_force_first": bool(dev_force),
            },
        )

        self._set_last_signal(ctx, bars)
        return sig
