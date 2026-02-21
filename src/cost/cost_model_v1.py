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
    """Return contract notional in NTD = price * multiplier * qty.

    - qty must be positive
    - unknown symbol => KeyError (regression expects this)
    - multiplier_override (if provided) overrides symbol mapping
    """
    # compat: symbol aliases
    if symbol == "TX":
        symbol = "TXF"
    elif symbol == "MTX":
        symbol = "MXF"

    if price <= 0:
        raise ValueError("price must be positive")
    if qty <= 0:
        raise ValueError("qty must be positive")

    if multiplier_override is not None:
        m = float(multiplier_override)
        if m <= 0:
            raise ValueError("multiplier_override must be positive")
        return float(price) * m * int(qty)

    if symbol not in DEFAULT_MULTIPLIER_BY_SYMBOL:
        raise KeyError(f"unknown symbol={symbol}")

    m = float(DEFAULT_MULTIPLIER_BY_SYMBOL.get(symbol, 0.0))
    if m <= 0:
        raise ValueError(f"unknown multiplier for symbol={symbol}; pass multiplier_override")
    return float(price) * m * int(qty)

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

    def calc_contract_value_ntd(self, *, price: float, symbol: str, qty: int):
        """Return TOTAL notional in NTD = price * multiplier * qty.

        - qty must be positive (ValueError)
        - unknown symbol => KeyError
        - rolling codes like TMFB6 map to TMF (base symbol)
        """
        if price <= 0:
            raise ValueError("price must be positive")
        if qty is None or int(qty) <= 0:
            raise ValueError("qty must be positive")

        sym = str(symbol or "")
        base = sym
        for b in ("TMF","TXF","MXF"):
            if sym.startswith(b):
                base = b
                break

        mult_map = globals().get("MULTIPLIER_BY_SYMBOL_V1") or globals().get("DEFAULT_MULTIPLIER_BY_SYMBOL") or {}
        if base not in mult_map:
            raise KeyError(base)
        m = float(mult_map[base])
        if m <= 0:
            raise KeyError(base)

        return float(price) * m * float(int(qty))


    def calc_round_trip_cost_ntd(self, *, price: float, symbol: str, qty: int):
        """Return round-trip total cost in NTD (fee + tax) for TOTAL qty.

        Returns:
          {
            "total_cost_ntd": ...,
            "fee_ntd": ...,
            "tax_ntd": ...,
            "details": {"qty":..., "multiplier":..., "tax_rate":...}
          }
        """
        # total notional (includes qty)
        contract_value_ntd = self.calc_contract_value_ntd(price=price, symbol=symbol, qty=qty)

        sym = str(symbol or "")
        base = sym
        for b in ("TMF","TXF","MXF"):
            if sym.startswith(b):
                base = b
                break

        # tax rate (per side)
        tax_rate = float(globals().get("TAX_RATE_V1") or globals().get("TAX_RATE_EQUITY_FUTURES") or 0.00002)

        # multiplier for details
        mult_map = globals().get("MULTIPLIER_BY_SYMBOL_V1") or globals().get("DEFAULT_MULTIPLIER_BY_SYMBOL") or {}
        if base not in mult_map:
            raise KeyError(base)
        multiplier = float(mult_map[base])

        # fee per side per contract
        fee_map = globals().get("DEFAULT_FEE_BY_SYMBOL_V1") or globals().get("DEFAULT_FEE_BY_SYMBOL") or globals().get("FEE_PER_SIDE_BY_SYMBOL") or {}
        spec = fee_map.get(base, fee_map.get(sym, 0.0))

        fee_per_side = 0.0
        if hasattr(spec, "per_side_total"):
            fee_per_side = float(getattr(spec, "per_side_total"))
        elif isinstance(spec, dict) and "per_side_total" in spec:
            fee_per_side = float(spec["per_side_total"])
        else:
            fee_per_side = float(spec or 0.0)

        # round-trip
        fee_ntd = fee_per_side * 2.0 * float(int(qty))
        tax_ntd = float(contract_value_ntd) * tax_rate * 2.0
        total = float(fee_ntd) + float(tax_ntd)

        return {
            "total_cost_ntd": float(total),
            "fee_ntd": float(fee_ntd),
            "tax_ntd": float(tax_ntd),
            "details": {
                "qty": int(qty),
                "multiplier": float(multiplier),
                "tax_rate": float(tax_rate),
            },
        }

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
        if int(qty) <= 0:
            raise ValueError("qty must be positive")
        return _call_accepting(calc_contract_value_ntd, price=price, symbol=symbol, qty=qty)  # type: ignore[name-defined]
    def calc_round_trip_cost_ntd(self, *, price: float, symbol: str, qty: int):
        """Return round-trip total cost in NTD for TOTAL qty.

        Must match scripts/m3_regression_cost_model_os_v1.sh expectations:
          total_cost_ntd = fee_ntd + tax_ntd
          fee_ntd = (fee_per_side_ntd_per_contract * qty) * 2
          tax_ntd = (price*multiplier*qty * tax_rate) * 2
        """
        q = int(qty)
        if q <= 0:
            raise ValueError("qty must be positive")
        px = float(price)
        if px <= 0:
            raise ValueError("price must be positive")

        # base symbol: allow rolling codes like TMFB6 -> TMF
        base = str(symbol or "")
        for b in ("TMF", "TXF", "MXF"):
            if base.startswith(b):
                base = b
                break

        # multiplier & fee map are held on self (per __init__ of compat class)
        m = float(self.multiplier_by_symbol.get(base, 0.0))
        if m <= 0:
            raise KeyError(base)

        tax_rate = float(getattr(self, "tax_rate", 0.0))
        contract_value_total = px * m * float(q)

        fee_obj = self.fee_by_symbol.get(base, 0.0)

        # fee_obj may be:
        # - number (float/int)
        # - FeeSpec-like object with per_side_total or (exchange_fee/clearing_fee/broker_commission)
        # - dict-like {exchange_fee, clearing_fee, broker_commission}
        if hasattr(fee_obj, "per_side_total"):
            fee_per_side = float(getattr(fee_obj, "per_side_total"))
        elif hasattr(fee_obj, "exchange_fee") or hasattr(fee_obj, "clearing_fee") or hasattr(fee_obj, "broker_commission"):
            fee_per_side = float(getattr(fee_obj, "exchange_fee", 0.0)) + float(getattr(fee_obj, "clearing_fee", 0.0)) + float(getattr(fee_obj, "broker_commission", 0.0))
        elif isinstance(fee_obj, dict):
            fee_per_side = float(fee_obj.get("exchange_fee", 0.0)) + float(fee_obj.get("clearing_fee", 0.0)) + float(fee_obj.get("broker_commission", 0.0))
        else:
            fee_per_side = float(fee_obj)
        fee_ntd = fee_per_side * float(q) * 2.0
        tax_ntd = contract_value_total * tax_rate * 2.0
        total = fee_ntd + tax_ntd

        return {
            "total_cost_ntd": float(total),
            "fee_ntd": float(fee_ntd),
            "tax_ntd": float(tax_ntd),
            "details": {
                "qty": q,
                "multiplier": m,
                "tax_rate": tax_rate,
            },
        }

