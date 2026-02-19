from __future__ import annotations
import os

from dataclasses import dataclass
from datetime import datetime, time
from pathlib import Path
from typing import Any, Dict, Optional
import json

# v18: minimal TW market calendar gate (bootstrap)
# - Primary goal: never attempt to trade when TWSE/TAIFEX are closed (holidays/weekends)
# - Allow override for backtests/sims via meta flags.

@dataclass(frozen=True)
class MarketOpenVerdict:
    ok: bool
    code: str
    reason: str
    details: Dict[str, Any]

def _load_closed_dates_2026() -> set:
    p = Path(__file__).resolve().parent / "tw_market_holidays_2026.json"
    try:
        obj = json.loads(p.read_text(encoding="utf-8"))
        return set(obj.get("closed_dates") or [])
    except Exception:
        # fail-safe: if calendar missing/broken, DO NOT hard-reject here.
        return set()

def _is_weekend(d: datetime) -> bool:
    return d.weekday() >= 5  # 5=Sat,6=Sun

def market_open_verdict(*, now: Optional[datetime] = None, meta: Optional[Dict[str, Any]] = None) -> MarketOpenVerdict:
    meta = meta or {}
    # v18 override knobs:
    if bool(meta.get("allow_market_closed")) or bool(meta.get("sim_mode")) or bool(meta.get("paper_mode")):
        return MarketOpenVerdict(True, "OK_MARKET_OVERRIDE", "market closed gate bypassed by meta override", {"meta_keys": list(meta.keys())})

    now = now or datetime.now()
    d = now.date().isoformat()

    # [REGTEST OVERRIDE] allow smoke/regression to bypass holiday/weekend/time gates
    # Only active when env var is explicitly set; does NOT affect production by default.
    _ig = (os.environ.get("TMF_IGNORE_MARKET_CALENDAR", "") or "").strip().lower()
    if _ig in ("1","true","yes","y","on"):
        return MarketOpenVerdict(True, "OK_MARKET_ENV_OVERRIDE", "market calendar bypassed by env", {"env": "TMF_IGNORE_MARKET_CALENDAR", "date": d})

    closed = _load_closed_dates_2026()
    if _is_weekend(now):
        return MarketOpenVerdict(False, "EXEC_MARKET_CLOSED", "weekend market closed", {"date": d, "weekday": now.weekday()})
    if d in closed:
        return MarketOpenVerdict(False, "EXEC_MARKET_CLOSED", "holiday market closed", {"date": d})

    # Optional: day-session time gate for TW futures/spot (bootstrap)
    # Keep conservative: only block obvious non-trading gaps. Night session varies by product.
    t = now.time()
    # If in the lunch break gap (approx 13:45-15:00), treat as closed unless explicitly overridden.
    if time(13,45) < t < time(15,0):
        return MarketOpenVerdict(False, "EXEC_MARKET_CLOSED", "between regular close and after-hours open", {"date": d, "time": t.isoformat(timespec="seconds")})

    return MarketOpenVerdict(True, "OK", "market open", {"date": d, "time": t.isoformat(timespec="seconds")})
