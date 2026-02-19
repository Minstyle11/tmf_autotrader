from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

@dataclass(frozen=True)
class PreflightVerdict:
    ok: bool
    code: str
    reason: str
    details: Dict[str, Any]

def check_shioaji_preflight(*, api: Any) -> PreflightVerdict:
    if api is None:
        return PreflightVerdict(False, "BROKER_API_NONE", "api is None", {})
    if not hasattr(api, "set_order_callback"):
        return PreflightVerdict(False, "BROKER_NO_ORDER_CALLBACK", "api lacks set_order_callback", {"type": str(type(api))})
    return PreflightVerdict(True, "OK", "preflight ok", {})
