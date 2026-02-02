"""
TMF AutoTrader - Slippage Model v1 (conservative, SIM/PAPER shared)

Goal:
- Provide a deterministic, conservative slippage estimate per fill.
- Keep it simple and safe for early phases.

Design:
- Slippage is expressed in "points" (price ticks / index points).
- Default is a fixed slippage per side by symbol.
- Optional: proportional slippage via bps of price (disabled by default).

Use:
- slp = calc_slippage(price, symbol, side, qty)
- Apply on fill price:
  - BUY:  exec_price = price + slp
  - SELL: exec_price = price - slp
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class SlippageSpec:
    # fixed points per side
    fixed_points: float = 1.0
    # optional proportional slippage in bps (0.01% = 1 bp). default 0 = disabled.
    bps: float = 0.0
    # max points cap (safety)
    max_points: float = 10.0


DEFAULT_SLIPPAGE_BY_SYMBOL: Dict[str, SlippageSpec] = {
    # Conservative defaults (can be tuned later with empirical data)
    "TMF": SlippageSpec(fixed_points=1.0, bps=0.0, max_points=10.0),
    "TXF": SlippageSpec(fixed_points=1.0, bps=0.0, max_points=10.0),
    "MXF": SlippageSpec(fixed_points=1.0, bps=0.0, max_points=10.0),
}


def calc_slippage_points(
    *,
    price: float,
    symbol: str,
    side: str,
    qty: float = 1.0,
    spec_override: Optional[SlippageSpec] = None,
) -> float:
    """
    Return slippage in points per side for this fill.
    Conservative rule:
      slippage = max(fixed_points, price * bps/10000), capped by max_points.
    qty currently not used (keep deterministic v1); reserved for later depth modeling.
    """
    if price <= 0:
        raise ValueError("price must be positive")
    side_u = str(side).upper()
    if side_u not in ("BUY", "SELL"):
        raise ValueError("side must be BUY or SELL")

    spec = spec_override if spec_override is not None else DEFAULT_SLIPPAGE_BY_SYMBOL.get(symbol, SlippageSpec())
    prop = (price * (float(spec.bps) / 10000.0)) if spec.bps and spec.bps > 0 else 0.0
    slp = max(float(spec.fixed_points), float(prop))
    slp = min(slp, float(spec.max_points))
    return float(slp)


def apply_slippage(
    *,
    price: float,
    symbol: str,
    side: str,
    qty: float = 1.0,
    spec_override: Optional[SlippageSpec] = None,
) -> float:
    """
    Return execution price after slippage.
      BUY  -> price + slippage
      SELL -> price - slippage
    """
    slp = calc_slippage_points(price=price, symbol=symbol, side=side, qty=qty, spec_override=spec_override)
    side_u = str(side).upper()
    if side_u == "BUY":
        return float(price + slp)
    return float(price - slp)


def _demo():
    price = 20000.0
    symbol = "TMF"
    qty = 2
    buy_px = apply_slippage(price=price, symbol=symbol, side="BUY", qty=qty)
    sell_px = apply_slippage(price=price, symbol=symbol, side="SELL", qty=qty)
    print("[demo] slippage_model_v1 OK")
    print("price =", price)
    print("symbol =", symbol)
    print("qty =", qty)
    print("buy_exec_price =", buy_px)
    print("sell_exec_price =", sell_px)
    print("slippage_points =", calc_slippage_points(price=price, symbol=symbol, side="BUY", qty=qty))


if __name__ == "__main__":
    _demo()
