from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

try:
    from typing_extensions import TypedDict, NotRequired, Literal, TypeGuard
except Exception:  # pragma: no cover
    # typing_extensions is required for Python 3.9 TypeGuard/NotRequired
    TypedDict = object  # type: ignore
    NotRequired = object  # type: ignore
    Literal = object  # type: ignore
    TypeGuard = object  # type: ignore

class RejectedOrder(TypedDict, total=False):
    ok: Literal[False]
    status: Literal["REJECTED"]
    broker_order_id: str
    safety: NotRequired[Dict[str, Any]]
    risk: NotRequired[Dict[str, Any]]
    exec: NotRequired[Dict[str, Any]]

def is_rejected_order(x: Any) -> "TypeGuard[RejectedOrder]":
    return (
        isinstance(x, dict)
        and bool(x.get("ok") is False)
        and str(x.get("status", "")).upper() == "REJECTED"
    )

def get_reject_codes(x: Any) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Return (safety_code, risk_code, exec_code) if x is a rejected dict; else (None,None,None)."""
    if not is_rejected_order(x):
        return (None, None, None)
    s = x.get("safety") if isinstance(x.get("safety"), dict) else {}
    r = x.get("risk") if isinstance(x.get("risk"), dict) else {}
    e = x.get("exec") if isinstance(x.get("exec"), dict) else {}
    return (
        (s.get("code") if isinstance(s, dict) else None),
        (r.get("code") if isinstance(r, dict) else None),
        (e.get("code") if isinstance(e, dict) else None),
    )
