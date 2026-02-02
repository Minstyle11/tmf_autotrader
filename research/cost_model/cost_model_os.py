"""
Cost Model OS (v18): scenario-based trading cost model (explicit + implicit + opportunity).
All research/backtests must include cost; costless metrics are invalid.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any

@dataclass(frozen=True)
class CostEstimate:
    fees: float
    slippage: float
    spread: float
    impact: float
    total: float
    details: Dict[str, Any]

def estimate_cost(*, symbol: str, qty: float, order_type: str, regime: str, session: str) -> CostEstimate:
    # Scaffold: return zeros; implement calibrated model next.
    return CostEstimate(0.0, 0.0, 0.0, 0.0, 0.0, {"symbol": symbol, "qty": qty, "order_type": order_type, "regime": regime, "session": session})
