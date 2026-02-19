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
    confidence_raw: Optional[float] = None  # raw (pre-adjust) confidence
    features: Dict[str, Any] = field(default_factory=dict)
    tags: Dict[str, Any] = field(default_factory=dict)

    def to_order_meta(self, *, strat_name: str, strat_version: str, ref_price: Optional[float], now_ts: Optional[str] = None, symbol: Optional[str] = None) -> Dict[str, Any]:
        meta: Dict[str, Any] = {}
        if ref_price is not None:
            meta["ref_price"] = float(ref_price)
        if self.stop_price is not None:
            meta["stop_price"] = float(self.stop_price)

        # Signal snapshot for audit/replay (stable schema; JSON-serializable)
        meta["signal"] = {
            "side": str(self.side),
            "qty": float(self.qty),
            "order_type": str(self.order_type),
            "price": (float(self.price) if self.price is not None else None),
            "stop_price": (float(self.stop_price) if self.stop_price is not None else None),
        }

        meta["strat"] = {
            "name": strat_name,
            "version": strat_version,
            "reason": self.reason,
            "confidence": float(self.confidence),
            "confidence_raw": (float(self.confidence_raw) if (self.confidence_raw is not None) else None),
            "features": dict(self.features or {}),
            "tags": dict(self.tags or {}),
        }
        # Runner audit context (optional but recommended for replay/reconcile)
        if now_ts is not None:
            meta.setdefault("audit", {})["now_ts"] = str(now_ts)
        if symbol is not None:
            meta.setdefault("audit", {})["symbol"] = str(symbol)

        # Stable attribution schema (v1): keep small + JSON-serializable
        meta["attribution_v1"] = {
            "signal": dict(meta.get("signal") or {}),
            "strat": dict(meta.get("strat") or {}),
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
