# -*- coding: utf-8 -*-
"""
TAIFEX Trading Calendar (v1) — OFFICIAL-LOCKED friendly
Goal:
- Provide a deterministic "is_market_closed" gate so SRE/keepfresh/autorestart/paper-live
  do NOT misclassify holiday/no-trade as feed failure.

Sources (design-time truth anchors):
- TAIFEX 2026 Holiday Schedule PDF (English)
- TAIFEX notices about Lunar New Year closure window and first trading day after CNY.

Runtime policy:
- No network calls. Calendar is deterministic and patchable via v18.x.
- Expose helpers for "closed reason" and "next open day".
"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional, Tuple

@dataclass(frozen=True)
class MarketClosedVerdict:
    closed: bool
    code: str
    reason: str
    next_open_day: Optional[str] = None  # YYYY-MM-DD

# Minimal 2026 closure anchors (can be expanded via v18.x patch)
# IMPORTANT:
# - Keep as exchange-level closures (TAIFEX no trading).
# - For 2026 CNY: Feb 15-20 closed; first trading day Feb 23.
# - Many orgs also treat Feb 12-13 as "TAIFEX Close" operationally; but exchange closure is Feb 15-20 per TAIFEX schedule.
TAIFEX_CLOSED_DATES_2026 = set([
    "2026-01-01",
    "2026-02-15","2026-02-16","2026-02-17","2026-02-18","2026-02-19","2026-02-20",
    "2026-02-28",
    "2026-04-03","2026-04-06",
    "2026-05-01",
    "2026-06-19",
    "2026-09-25",
    "2026-10-09",
])

def _ymd(d: date) -> str:
    return d.strftime("%Y-%m-%d")

def is_taifex_closed_day(d: date) -> bool:
    if d.year == 2026:
        return _ymd(d) in TAIFEX_CLOSED_DATES_2026
    # Default: unknown years -> not closed by this static table (caller should add via patch when needed)
    return False

def next_open_day(d: date, *, max_scan_days: int = 60) -> Optional[str]:
    cur = d
    for _ in range(max_scan_days):
        cur = cur + timedelta(days=1)
        # NOTE: We only handle exchange closures here; weekends are assumed closed too.
        if cur.weekday() >= 5:
            continue
        if not is_taifex_closed_day(cur):
            return _ymd(cur)
    return None

def market_closed_verdict(d: date) -> MarketClosedVerdict:
    ymd = _ymd(d)
    if d.weekday() >= 5:
        return MarketClosedVerdict(True, "MARKET_CLOSED_WEEKEND", f"Weekend closed ({ymd})", next_open_day(d))
    if is_taifex_closed_day(d):
        return MarketClosedVerdict(True, "MARKET_CLOSED_HOLIDAY", f"TAIFEX holiday closed ({ymd})", next_open_day(d))
    return MarketClosedVerdict(False, "MARKET_OPEN", f"Trading day ({ymd})", None)

def market_closed_now_taipei(now=None) -> MarketClosedVerdict:
    # Avoid tz deps: caller should run on Asia/Taipei host; use local date.
    if now is None:
        now = datetime.now()
    return market_closed_verdict(now.date())

# late import to avoid datetime shadow
from datetime import datetime
