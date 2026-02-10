from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Literal

Side = Literal["BUY", "SELL"]
OrderType = Literal["MARKET", "LIMIT"]

@dataclass
class StrategySignalV1:
    side: Side
    qty: float
    order_type: OrderType = "MARKET"
    price: Optional[float] = None

    # v18/m2 strict: stop can be required by risk gate; strategy should provide when it can.
    stop_price: Optional[float] = None

    # Attribution fields
    reason: str = ""
    confidence: float = 0.5  # 0..1
    features: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, Any] = field(default_factory=dict)

    def to_order_meta(self, *, strat_name: str, strat_version: str, ref_price: Optional[float]) -> Dict[str, Any]:
        meta: Dict[str, Any] = {}
        if ref_price is not None:
            meta["ref_price"] = float(ref_price)
        if self.stop_price is not None:
            meta["stop_price"] = float(self.stop_price)

        meta["strat"] = {
            "name": strat_name,
            "version": strat_version,
            "reason": self.reason,
            "confidence": float(self.confidence),
            "features": dict(self.features or {}),
            "tags": dict(self.tags or {}),
        }
        return meta

class StrategyContextV1:
    """Lightweight context carrier.
    Runner/engine can extend this over time without breaking strategies.
    """
    def __init__(self, *, now_ts: str, symbol: str, state: Optional[Dict[str, Any]] = None):
        self.now_ts = now_ts
        self.symbol = symbol
        self.state: Dict[str, Any] = state or {}

class StrategyBaseV1:
    name: str = "StrategyBaseV1"
    version: str = "v1"

    def on_bar_1m(self, ctx: StrategyContextV1, bar: Dict[str, Any]) -> Optional[StrategySignalV1]:
        """Return a signal when you want to open/flip; otherwise None.
        bar: {ts_min, o,h,l,c,v,...} (dict) - keep generic to avoid tight coupling.
        """
        return None
