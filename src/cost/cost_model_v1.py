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


TAX_RATE_V1 = TAX_RATE_EQUITY_FUTURES  # compatibility alias for regressions

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


def calc_contract_value_ntd(*, price: float, symbol: str, qty: int = 1, multiplier_override: Optional[float] = None) -> float:
    """Return per-contract notional in NTD = price * multiplier.

    NOTE: Some broker contract objects may report multiplier as 0/empty; keep a canonical mapping here.
    """
    # compat: symbol aliases + explicit multiplier override
    if symbol == "TX":
        symbol = "TXF"
    elif symbol == "MTX":
        symbol = "MXF"
    if multiplier_override is not None:
        return float(price) * float(multiplier_override)

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
# --- Compatibility API (CostModelV1) ---
# This layer exists to keep regression scripts stable.
from dataclasses import dataclass
from typing import Optional, Dict

@dataclass(frozen=True)
class CostModelConfigV1:
    symbol: str
    tax_rate: float = TAX_RATE_EQUITY_FUTURES
    fee_override: Optional[FeeSpec] = None
    multiplier_override: Optional[float] = None

class CostModelV1:

    def calc_contract_value_ntd(self, *, price: float, symbol: str, qty: int = 1) -> float:
        # regression compatibility: return TOTAL notional including qty
        per = calc_contract_value_ntd(price=price, symbol=symbol)
        return float(per) * float(qty)

    def __init__(
        self,
        *,
        symbol: str,
        tax_rate: float = TAX_RATE_EQUITY_FUTURES,
        fee_override: Optional[FeeSpec] = None,
        multiplier_override: Optional[float] = None,
    ) -> None:
        self.symbol = str(symbol)
        self.tax_rate = float(tax_rate)
        self.fee_override = fee_override
        self.multiplier_override = float(multiplier_override) if multiplier_override is not None else None

    def contract_value_ntd(self, *, price: float) -> float:
        return calc_contract_value_ntd(price=price, symbol=self.symbol, multiplier_override=self.multiplier_override)

    def round_trip_cost_ntd(self, *, price: float, qty: int = 1) -> dict:
        cv = self.contract_value_ntd(price=price)
        return calc_round_trip_cost_ntd(
            contract_value_ntd=cv,
            symbol=self.symbol,
            qty=int(qty),
            tax_rate=self.tax_rate,
            fee_override=self.fee_override,
        )

# Backward/alternate names some scripts may import
CostModel = CostModelV1
TaifexCostModelV1 = CostModelV1

def build_cost_model(*, symbol: str, cfg: Optional[CostModelConfigV1] = None) -> CostModelV1:
    if cfg is None:
        return CostModelV1(symbol=symbol)
    return CostModelV1(
        symbol=cfg.symbol,
        tax_rate=cfg.tax_rate,
        fee_override=cfg.fee_override,
        multiplier_override=cfg.multiplier_override,
    )

def estimate_cost(*, symbol: str, price: float, qty: int = 1) -> dict:
    m = CostModelV1(symbol=symbol)
    return m.round_trip_cost_ntd(price=float(price), qty=int(qty))

def calc_cost(*, symbol: str, price: float, qty: int = 1) -> dict:
    return estimate_cost(symbol=symbol, price=price, qty=qty)
# --- FeeSpecV1 alias (regression compatibility) ---
# FEE_SPEC_V1_ALIAS_GUARD
try:
    FeeSpecV1 = FeeSpec  # type: ignore
except Exception:
    pass

MULTIPLIER_BY_SYMBOL_V1 = DEFAULT_MULTIPLIER_BY_SYMBOL  # compatibility alias for regressions

# === COMPAT_COSTMODEL_V1_BEGIN ===
# NOTE: compatibility layer for scripts/m3_regression_cost_model_os_v1.sh
# - expected exports: CostModelV1, FeeSpecV1, TAX_RATE_V1, MULTIPLIER_BY_SYMBOL_V1
# - CostModelV1() must be constructible with no args and provide methods:
#   calc_contract_value_ntd / calc_round_trip_cost_ntd
import inspect as _inspect

try:
    FeeSpecV1 = FeeSpec  # type: ignore[name-defined]
except NameError:
    FeeSpecV1 = None  # should never happen, but keep import-safe

try:
    TAX_RATE_V1 = TAX_RATE_EQUITY_FUTURES  # type: ignore[name-defined]
except NameError:
    TAX_RATE_V1 = 0.0

try:
    MULTIPLIER_BY_SYMBOL_V1 = DEFAULT_MULTIPLIER_BY_SYMBOL  # type: ignore[name-defined]
except NameError:
    MULTIPLIER_BY_SYMBOL_V1 = {}

try:
    FEE_BY_SYMBOL_V1 = DEFAULT_FEE_BY_SYMBOL  # type: ignore[name-defined]
except NameError:
    FEE_BY_SYMBOL_V1 = {}

def _call_accepting(fn, **kwargs):
    """Call fn with only kwargs it accepts; also auto-map qty->(qty/contracts/quantity/n) if needed."""
    sig = _inspect.signature(fn)
    params = sig.parameters
    # if fn supports **kwargs, pass through all
    if any(p.kind == p.VAR_KEYWORD for p in params.values()):
        return fn(**kwargs)

    accept = set(params.keys())

    # normalize common aliases
    if "qty" in kwargs and "qty" not in accept:
        q = kwargs["qty"]
        for alt in ("quantity", "contracts", "n", "size"):
            if alt in accept and alt not in kwargs:
                kwargs[alt] = q
                break

    filtered = {k: v for k, v in kwargs.items() if k in accept}
    return fn(**filtered)

class CostModelV1:
    """Thin wrapper around module-level cost functions (backward compat)."""
    def __init__(self, fee_by_symbol=None, multiplier_by_symbol=None, tax_rate=None):
        self.fee_by_symbol = fee_by_symbol or FEE_BY_SYMBOL_V1
        self.multiplier_by_symbol = multiplier_by_symbol or MULTIPLIER_BY_SYMBOL_V1
        self.tax_rate = TAX_RATE_V1 if tax_rate is None else tax_rate

    def calc_contract_value_ntd(self, *, price: float, symbol: str, qty: int):
        return _call_accepting(calc_contract_value_ntd, price=price, symbol=symbol, qty=qty)  # type: ignore[name-defined]

    def calc_round_trip_cost_ntd(self, *, price: float, symbol: str, qty: int):
        return _call_accepting(calc_round_trip_cost_ntd, price=price, symbol=symbol, qty=qty)  # type: ignore[name-defined]

# === COMPAT_COSTMODEL_V1_END ===
