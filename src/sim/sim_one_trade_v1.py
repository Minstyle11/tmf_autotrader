from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

from src.cost.cost_model_v1 import calc_round_trip_cost_ntd, FeeSpec


Side = Literal["BUY", "SELL"]


@dataclass(frozen=True)
class Trade:
    symbol: str           # e.g. "TMF"
    side: Side            # BUY=long, SELL=short (open)
    qty: int
    entry: float          # price
    exit: float           # price
    multiplier: float     # NTD per point per contract (placeholder; set correctly later)
    fee_exchange: float = 0.0
    fee_clearing: float = 0.0
    fee_broker: float = 0.0


def calc_one_trade_pnl_ntd(t: Trade) -> dict:
    if t.qty <= 0:
        raise ValueError("qty must be positive")
    if t.entry <= 0 or t.exit <= 0:
        raise ValueError("entry/exit must be positive")
    if t.multiplier <= 0:
        raise ValueError("multiplier must be positive")

    direction = 1.0 if t.side == "BUY" else -1.0
    gross_pnl = (t.exit - t.entry) * t.multiplier * t.qty * direction

    # notional per contract for tax calc: price * multiplier
    # NOTE: For TW index futures, multiplier is NTD/point; price is points => price*multiplier = NTD notional per contract.
    contract_value_ntd = t.entry * t.multiplier

    fee = FeeSpec(exchange_fee=t.fee_exchange, clearing_fee=t.fee_clearing, broker_commission=t.fee_broker)
    cost = calc_round_trip_cost_ntd(
        contract_value_ntd=contract_value_ntd,
        symbol=t.symbol,
        qty=t.qty,
        fee_override=fee,
    )

    net_pnl = gross_pnl - cost["total_round_trip_ntd_all"]

    return {
        "trade": t.__dict__,
        "gross_pnl_ntd": float(gross_pnl),
        "cost_breakdown": cost,
        "net_pnl_ntd": float(net_pnl),
    }


def _demo():
    # IMPORTANT: multiplier below is a placeholder for pipeline wiring.
    # We'll replace with the correct TMF multiplier from contract specs in the next steps.
    t = Trade(
        symbol="TMF",
        side="BUY",
        qty=2,
        entry=20000.0,
        exit=20010.0,
        multiplier=50.0,
        fee_exchange=4.8,
        fee_clearing=3.2,
        fee_broker=0.0,
    )
    out = calc_one_trade_pnl_ntd(t)
    print("[demo] sim_one_trade_v1 OK")
    print("gross_pnl_ntd =", out["gross_pnl_ntd"])
    print("total_round_trip_cost_ntd =", out["cost_breakdown"]["total_round_trip_ntd_all"])
    print("net_pnl_ntd =", out["net_pnl_ntd"])


if __name__ == "__main__":
    _demo()
