"""
TMF AutoTrader - Cost Model v1 (SIM/PAPER/LIVE shared)
Components (round-trip = open+close):
  - Futures transaction tax (TW, equity index futures): 2/100000 = 0.00002 per side
  - Exchange + clearing fees: configurable per contract (NTD/contract/side)
  - Broker commission: configurable (NTD/contract/side)

Preferred: use calc_contract_value_ntd(price, symbol) to avoid wrong multiplier.
Caller MAY still provide contract_value_ntd explicitly when needed.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict


# Taiwan futures transaction tax for equity index futures (per side)
TAX_RATE_EQUITY_FUTURES = 0.00002  # 2 / 100000


@dataclass(frozen=True)
class FeeSpec:
    # NTD per contract per side
    exchange_fee: float = 0.0
    clearing_fee: float = 0.0
    broker_commission: float = 0.0

    @property
    def per_side_total(self) -> float:
        return float(self.exchange_fee + self.clearing_fee + self.broker_commission)


# Defaults can be overridden later by config; keep conservative.
DEFAULT_FEE_BY_SYMBOL: Dict[str, FeeSpec] = {
    "TMF": FeeSpec(exchange_fee=4.8, clearing_fee=3.2, broker_commission=0.0),
    "TXF": FeeSpec(exchange_fee=0.0, clearing_fee=0.0, broker_commission=0.0),
    "MXF": FeeSpec(exchange_fee=0.0, clearing_fee=0.0, broker_commission=0.0),
}




# Contract multipliers (TAIFEX index futures point value)
# TMF: 10 NTD/point, MXF: 50 NTD/point, TXF: 200 NTD/point
DEFAULT_MULTIPLIER_BY_SYMBOL: Dict[str, float] = {
    "TMF": 10.0,
    "MXF": 50.0,
    "TXF": 200.0,
}


def calc_contract_value_ntd(*, price: float, symbol: str, multiplier_override: Optional[float] = None) -> float:
    """Return per-contract notional in NTD = price * multiplier.

    NOTE: Some broker contract objects may report multiplier as 0/empty; keep a canonical mapping here.
    """
    if price <= 0:
        raise ValueError("price must be positive")
    m = float(multiplier_override) if multiplier_override is not None else float(DEFAULT_MULTIPLIER_BY_SYMBOL.get(symbol, 0.0))
    if m <= 0:
        raise ValueError(f"unknown multiplier for symbol={symbol}; pass multiplier_override")
    return float(price) * m

def calc_round_trip_cost_ntd(
    *,
    contract_value_ntd: float,
    symbol: str,
    qty: int = 1,
    tax_rate: float = TAX_RATE_EQUITY_FUTURES,
    fee_override: Optional[FeeSpec] = None,
) -> dict:
    """
    Round-trip = open + close.
    contract_value_ntd: per-contract notional in NTD (price * multiplier).
    qty: contracts.
    tax_rate: per-side rate on notional.
    """
    if qty <= 0:
        raise ValueError("qty must be positive")
    if contract_value_ntd <= 0:
        raise ValueError("contract_value_ntd must be positive")

    fee = fee_override if fee_override is not None else DEFAULT_FEE_BY_SYMBOL.get(symbol, FeeSpec())

    # Tax: per side; round-trip tax = notional * tax_rate * 2
    tax_round_trip = contract_value_ntd * tax_rate * 2.0

    # Fees: per contract per side; round-trip fee = per_side_total * 2
    fee_round_trip = fee.per_side_total * 2.0

    total_per_contract = tax_round_trip + fee_round_trip
    total_all = total_per_contract * qty

    return {
        "symbol": symbol,
        "qty": int(qty),
        "contract_value_ntd": float(contract_value_ntd),
        "tax_rate_per_side": float(tax_rate),
        "tax_round_trip_ntd_per_contract": float(tax_round_trip),
        "fee_per_side_ntd": float(fee.per_side_total),
        "fee_round_trip_ntd_per_contract": float(fee_round_trip),
        "total_round_trip_ntd_per_contract": float(total_per_contract),
        "total_round_trip_ntd_all": float(total_all),
        "fee_spec": {
            "exchange_fee": float(fee.exchange_fee),
            "clearing_fee": float(fee.clearing_fee),
            "broker_commission": float(fee.broker_commission),
        },
    }


def _demo():
    demo_price = 20000.0
    demo_notional = calc_contract_value_ntd(price=demo_price, symbol="TMF")
    out = calc_round_trip_cost_ntd(contract_value_ntd=demo_notional, symbol="TMF", qty=2)
    print("[demo] cost_model_v1 OK")
    print(f"price = {demo_price}")
    for k in [
        "symbol","qty","contract_value_ntd",
        "tax_round_trip_ntd_per_contract",
        "fee_round_trip_ntd_per_contract",
        "total_round_trip_ntd_all",
        "fee_spec",
    ]:
        print(f"{k} = {out[k]}")


if __name__ == "__main__":
    _demo()
