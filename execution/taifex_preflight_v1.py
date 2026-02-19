from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from typing import Any, Dict, List, Optional

# TAIFEX official rule anchor (English site):
# - Market order max qty: 10 (regular), 5 (after-hours) since 2019-05-27
# - Limit/MWP max qty: futures 100 (most), options 200, single-stock futures/options 499 (see TAIFEX pages)
# NOTE: We encode the subset needed for TX/MTX/TMF (index futures) first:
#   - market: 10/5, limit: 100, mwp: 100 (for stock index futures)
#
# This module is an OrderGuard "hard gate": it never places orders; it only returns verdict + (optional) split plan.

@dataclass(frozen=True)
class PreflightVerdict:
    ok: bool
    code: str
    reason: str
    details: Dict[str, Any]

def _session_hint_from_time(now: datetime) -> str:
    """
    Infer TAIFEX session for index futures:
    - Regular trading session roughly 08:45-13:45 (Taipei time)
    - After-hours otherwise (15:00-05:00 next day; there is a gap 13:45-15:00)
    We keep it conservative: if not confidently in regular window, treat as after-hours.
    """
    t = now.time()
    if time(8, 45) <= t <= time(13, 45):
        return "REGULAR"
    return "AFTER_HOURS"

def _normalize_session_hint(raw: str) -> str:
    """Normalize caller-provided session hints to canonical TAIFEX sessions.
    Accepts historical aliases used across scripts:
      - DAY/REGULAR/D/R -> REGULAR
      - NIGHT/AFTER_HOURS/AH/N -> AFTER_HOURS
    Unknown values are returned uppercased as-is (fail-safe => treated as AFTER_HOURS by _max_qty).
    """
    v = str(raw or "").strip().upper()
    if v in {"DAY", "REGULAR", "D", "R"}:
        return "REGULAR"
    if v in {"NIGHT", "AFTER_HOURS", "AH", "N"}:
        return "AFTER_HOURS"
    return v

def _max_qty(order_type: str, session: str) -> int:
    ot = (order_type or "").strip().upper()
    ss = (session or "").strip().upper()

    if ot == "MARKET":
        return 10 if ss == "REGULAR" else 5

    # Limit / MWP for stock index futures: 100 contracts per order (TAIFEX)
    if ot in ("LIMIT", "MWP"):
        return 100

    # Unknown type: fail safe => reject
    return 0

def _plan_splits(total_qty: int, max_per_order: int) -> List[int]:
    if max_per_order <= 0:
        return []
    n_full = total_qty // max_per_order
    rem = total_qty % max_per_order
    out: List[int] = [max_per_order] * n_full
    if rem:
        out.append(rem)
    return out

def check_taifex_preflight(
    *,
    symbol: str = None,
    code: str = None,
    side: str = None,
    order_type: str,
    qty: float,
    price: float = None,

    now: Optional[datetime] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> PreflightVerdict:
    meta = meta or {}
    try:
        qty_f = float(qty)
    except Exception:
        return PreflightVerdict(False, "ORDER_QTY_INVALID", "qty must be numeric", {"qty": qty})
    if qty_f <= 0:
        return PreflightVerdict(False, "ORDER_QTY_INVALID", "qty must be positive", {"qty": qty})
    if abs(qty_f - round(qty_f)) > 1e-9:
        return PreflightVerdict(False, "ORDER_QTY_INVALID", "qty must be integer", {"qty": qty})
    qty_int = int(round(qty_f))

    # normalize code
    if code is None and symbol is not None:
        code = str(symbol)
    code = str(code or "").strip() or "UNKNOWN"

    if qty_int <= 0:
        return PreflightVerdict(False, "ORDER_QTY_INVALID", "qty must be positive", {"qty": qty_int})

    # Allow explicit override by meta for research-only scenarios
    if bool(meta.get("allow_preflight_bypass")):
        return PreflightVerdict(True, "OK_PREFLIGHT_BYPASS", "preflight bypassed by meta", {"meta_keys": list(meta.keys())})

    now = now or datetime.now()
    # Prefer explicit session hint if supplied, else infer from time.
    raw_hint = meta.get("session_hint")
    if raw_hint is None:
        raw_hint = meta.get("session")
    if raw_hint is None and "is_night" in meta:
        raw_hint = "NIGHT" if bool(meta.get("is_night")) else "DAY"

    session = _normalize_session_hint(raw_hint)
    if not session:
        session = _session_hint_from_time(now)

    # B3) Regime: DPB/DPBM risk flag blocks (treat exchange protection as regime).
    if bool((meta or {}).get("regime_dpb_risk")):
        return PreflightVerdict(
            False,
            "EXEC_TAIFEX_REGIME_DPB_RISK",
            "regime indicates DPB/DPBM risk; block order to avoid exchange-protection rejects",
            {"order_type": order_type, "session": session, "regime_dpb_risk": True},
        )

    # B2) MWP must have same-side best price to derive exchange-defined converted LIMIT.
    # If missing, TAIFEX may reject the order (no same-side best price as conversion anchor).
    if (order_type or "").strip().upper() == "MWP":
        bsl = (meta or {}).get("best_same_side_limit")
        try:
            bsl_ok = (bsl is not None) and (float(bsl) > 0)
        except Exception:
            bsl_ok = False
        if not bsl_ok:
            return PreflightVerdict(
                False,
                "EXEC_TAIFEX_MWP_NO_SAMESIDE_LIMIT",
                "MWP requires best_same_side_limit (same-side best price) to derive converted limit",
                {"order_type": order_type, "session": session, "best_same_side_limit": bsl},
            )

    max_per_order = _max_qty(order_type, session)
    if max_per_order <= 0:
        return PreflightVerdict(
            False,
            "ORDER_TYPE_UNSUPPORTED",
            "unsupported order_type for TAIFEX preflight",
            {"order_type": order_type, "session": session},
        )

    if qty_int <= max_per_order:
        return PreflightVerdict(True, "OK", "within TAIFEX order-size limits", {
            "code": code,
            "order_type": order_type,
            "session": session,
            "qty": qty_int,
            "max_per_order": max_per_order,
        })

    # Exceeds limit => hard gate (policy-driven split-or-reject)
    splits = _plan_splits(qty_int, max_per_order)
    allow_split = bool(meta.get("allow_split"))  # caller decides whether it will actually split
    if (order_type or '').strip().upper() == 'MARKET':
        err_code = 'EXEC_TAIFEX_MKT_QTY_LIMIT'
        # wrapper SPLIT branch expects 'limit' + 'session_hint'
        extra = {'limit': max_per_order, 'session_hint': session}
    else:
        err_code = 'TAIFEX_ORDER_SIZE_LIMIT'
        extra = {}
    return PreflightVerdict(
        False,
        err_code,
        "qty exceeds TAIFEX per-order maximum",
        {
            "code": code,
            "order_type": order_type,
            "session": session,
            "qty": qty_int,
            "max_per_order": max_per_order,
            "allow_split": allow_split,
            "suggested_splits": splits,
            **extra,
        },
    )
