from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional

# v18.1-B: TAIFEX local exchange hard constraints preflight (avoid rejected / bad orders)

@dataclass(frozen=True)
class PreflightVerdict:
    ok: bool
    code: str
    reason: str
    details: Dict[str, Any]

def _is_after_hours(meta: Dict[str, Any]) -> bool:
    s = str(meta.get("session_hint", "") or "").upper()
    return s in {"NIGHT", "AFTER_HOURS", "AH"}

def _order_type_norm(order_type: str) -> str:
    return str(order_type or "").strip().upper()

def check_taifex_preflight(
    *,
    symbol: str,
    side: str,
    qty: float,
    order_type: str,
    price: Optional[float],
    meta: Optional[Dict[str, Any]] = None,
) -> PreflightVerdict:
    meta = meta or {}
    ot = _order_type_norm(order_type)
    q = float(qty)

    # B1) Market order size limits: day<=10, after-hours<=5
    if ot == "MARKET":
        lim = 5 if _is_after_hours(meta) else 10
        if q > float(lim):
            return PreflightVerdict(
                False,
                "EXEC_TAIFEX_MKT_QTY_LIMIT",
                "market order qty exceeds TAIFEX limit (day=10, after-hours=5); must split or reject",
                {"qty": q, "limit": lim, "session_hint": meta.get("session_hint")},
            )

    # B2) MWP exchange definition: need same-side best limit price
    is_mwp = (ot == "MWP") or bool(meta.get("mwp"))
    if is_mwp:
        best_same = meta.get("best_same_side_limit")
        if best_same is None:
            return PreflightVerdict(
                False,
                "EXEC_TAIFEX_MWP_NO_SAMESIDE_LIMIT",
                "MWP requires same-side best limit price (exchange definition); missing best_same_side_limit",
                {"side": side, "order_type": ot},
            )
        if meta.get("protection_points") is None:
            return PreflightVerdict(
                True,
                "OK_TAIFEX_MWP_NO_PROTECTION_POINTS",
                "MWP provided best_same_side_limit but protection_points missing; caller should set per product table",
                {"best_same_side_limit": best_same},
            )

    # B3) DPB/price-limit regime: conservative flag gate
    if bool(meta.get("regime_dpb_risk")):
        return PreflightVerdict(
            False,
            "EXEC_TAIFEX_REGIME_DPB_RISK",
            "DPB/price-limit regime risk flagged; block or reduce aggressiveness per policy",
            {"regime_dpb_risk": True},
        )

    return PreflightVerdict(True, "OK", "taifex preflight pass", {"order_type": ot})
