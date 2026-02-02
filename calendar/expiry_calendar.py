from __future__ import annotations

"""
V18 scaffold: calendar/expiry_calendar.py

This is a placeholder created to align repo structure with TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18.
Implement according to v18 requirements before production use.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class _ScaffoldInfo:
    module: str = "calendar/expiry_calendar.py"
    status: str = "SCAFFOLDED"
    note: str = "TODO: implement per v18"


def get_scaffold_info() -> Dict[str, Any]:
    return {"module": "calendar/expiry_calendar.py", "status": "SCAFFOLDED", "todo": True}


def _not_implemented(*args: Any, **kwargs: Any) -> None:
    raise NotImplementedError("V18 scaffold placeholder: implement per v18")


# public surface (safe default)
__all__ = ["get_scaffold_info", "_not_implemented"]
