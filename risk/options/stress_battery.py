"""
Stress Battery OS (v18): run stress scenarios + enforce gate.
v1 scope:
  - Deterministic scenario engine (no external deps)
  - Computes worst_loss_ntd and worst_margin_ratio
  - Caller must provide contract specs (point_value_ntd, margin_per_contract_ntd)
  - Emits machine-readable details for drill reports
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List, Optional


@dataclass(frozen=True)
class ContractSpec:
    symbol: str
    point_value_ntd: float          # NTD per 1 price point
    margin_per_contract_ntd: float  # initial margin (approx) per contract


@dataclass(frozen=True)
class Position:
    symbol: str
    side: str   # "LONG" or "SHORT"
    qty: float
    entry_price: float


@dataclass(frozen=True)
class Scenario:
    name: str
    shock_points: float  # +points move vs entry reference


@dataclass(frozen=True)
class StressResult:
    ok: bool
    worst_loss_ntd: float
    worst_margin_ratio: float
    details: Dict[str, Any]


def _pnl_points(pos: Position, shock_points: float) -> float:
    # Positive pnl_points = profit; Negative = loss (in points)
    s = pos.side.upper()
    if s == "LONG":
        return shock_points
    if s == "SHORT":
        return -shock_points
    raise ValueError(f"bad side={pos.side}")


def _loss_ntd_for(pos: Position, spec: ContractSpec, shock_points: float) -> float:
    pnl_points = _pnl_points(pos, shock_points)
    pnl_ntd = pnl_points * spec.point_value_ntd * pos.qty
    return max(0.0, -pnl_ntd)  # loss only


def run_stress_battery(
    *,
    portfolio_state: Dict[str, Any],
    contract_specs: List[ContractSpec],
    scenarios: Optional[List[Scenario]] = None,
    gate_max_loss_ntd: Optional[float] = None,
    gate_max_margin_ratio: Optional[float] = None,
) -> StressResult:
    """
    portfolio_state (v1 expected):
      {
        "positions": [{"symbol":"TMF","side":"LONG","qty":1,"entry_price":31775.0}, ...],
        "cash_ntd": 800000.0
      }
    """
    pos_raw = portfolio_state.get("positions") or []
    cash_ntd = float(portfolio_state.get("cash_ntd", 0.0))

    spec_map: Dict[str, ContractSpec] = {s.symbol: s for s in contract_specs}

    if scenarios is None:
        scenarios = [
            Scenario("shock_-50pt", -50.0),
            Scenario("shock_+50pt", +50.0),
            Scenario("shock_-100pt", -100.0),
            Scenario("shock_+100pt", +100.0),
            Scenario("gap_-200pt", -200.0),
            Scenario("gap_+200pt", +200.0),
        ]

    positions: List[Position] = []
    missing_specs: List[str] = []
    for r in pos_raw:
        p = Position(
            symbol=str(r["symbol"]),
            side=str(r["side"]),
            qty=float(r["qty"]),
            entry_price=float(r["entry_price"]),
        )
        positions.append(p)
        if p.symbol not in spec_map:
            missing_specs.append(p.symbol)

    if missing_specs:
        return StressResult(
            ok=False,
            worst_loss_ntd=float("inf"),
            worst_margin_ratio=float("inf"),
            details={
                "code": "MISSING_CONTRACT_SPEC",
                "missing_symbols": sorted(set(missing_specs)),
                "hint": "pass contract_specs=[ContractSpec(...)] with point_value_ntd + margin_per_contract_ntd",
            },
        )

    total_margin = 0.0
    for p in positions:
        total_margin += abs(p.qty) * spec_map[p.symbol].margin_per_contract_ntd
    worst_margin_ratio = (total_margin / cash_ntd) if cash_ntd > 0 else float("inf")

    per_scn = []
    worst_loss = 0.0
    worst = None
    for scn in scenarios:
        loss = 0.0
        per_pos = []
        for p in positions:
            spec = spec_map[p.symbol]
            loss_i = _loss_ntd_for(p, spec, scn.shock_points)
            loss += loss_i
            per_pos.append({"symbol": p.symbol, "side": p.side, "qty": p.qty, "loss_ntd": loss_i})
        per_scn.append({"scenario": scn.name, "shock_points": scn.shock_points, "loss_ntd": loss, "by_pos": per_pos})
        if loss > worst_loss:
            worst_loss = loss
            worst = per_scn[-1]

    ok = True
    gate = {}
    if gate_max_loss_ntd is not None:
        gate["gate_max_loss_ntd"] = float(gate_max_loss_ntd)
        if worst_loss > float(gate_max_loss_ntd):
            ok = False
    if gate_max_margin_ratio is not None:
        gate["gate_max_margin_ratio"] = float(gate_max_margin_ratio)
        if worst_margin_ratio > float(gate_max_margin_ratio):
            ok = False

    return StressResult(
        ok=ok,
        worst_loss_ntd=float(worst_loss),
        worst_margin_ratio=float(worst_margin_ratio),
        details={
            "code": "OK" if ok else "STRESS_GATE_FAIL",
            "cash_ntd": cash_ntd,
            "total_margin_ntd_est": total_margin,
            "worst": worst,
            "scenarios": per_scn,
            "gate": gate,
        },
    )
