from __future__ import annotations

"""execution/order_guard.py (v18.1 minimal viable)

OrderGuard is the *single* pre-trade hard-gate façade for execution constraints.
Goal:
- Centralize TAIFEX hard constraints (order-size limits, MWP requirements, regime blocks)
- Provide a stable public surface for OMS wrapper / future broker adapters
- Keep policy decisions (split vs reject) at caller; OrderGuard only returns verdict + plan

This file replaces the old scaffold placeholder.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional, Union

from execution.taifex_preflight_v1 import PreflightVerdict, check_taifex_preflight


@dataclass(frozen=True)
class OrderGuardVerdict:
    ok: bool
    code: str
    reason: str
    details: Dict[str, Any]

    @staticmethod
    def from_preflight(v: PreflightVerdict) -> "OrderGuardVerdict":
        return OrderGuardVerdict(ok=bool(v.ok), code=str(v.code), reason=str(v.reason), details=dict(v.details or {}))



def _normalize_price_type_to_ot(raw: str) -> str:
    """Normalize caller order_type/price_type to TAIFEX canonical OT.
    Accepts: MARKET/MKT, LIMIT/LMT, MWP/MKP.
    (Keep small + local to avoid importing private helpers.)
    """
    v = str(raw or "").strip().upper()
    if v in {"MARKET", "MKT"}:
        return "MARKET"
    if v in {"LIMIT", "LMT"}:
        return "LIMIT"
    if v in {"MWP", "MKP"}:
        return "MWP"
    return v

def _extract_tif(meta):
    """Extract Time-In-Force (ROD/IOC/FOK) if caller provides it.
    We accept common keys to reduce integration friction.
    """
    if not meta:
        return ""
    for k in ("tif", "time_in_force", "shioaji_order_type", "order_type_tif", "tif_type", "order_type"):
        if k in meta and meta.get(k) is not None:
            return str(meta.get(k)).strip().upper()
    return ""


def _with_details(out, details: dict):
    """Return a new verdict object with updated details in a type-safe way.
    Supports: NamedTuple (_replace), dataclass (dataclasses.replace), and plain objects (__dict__).
    Never raises (best-effort), but tries hard to persist details.
    """
    try:
        if hasattr(out, "_replace"):
            return out._replace(details=details)
    except Exception:
        pass
    try:
        import dataclasses
        if dataclasses.is_dataclass(out):
            return dataclasses.replace(out, details=details)
    except Exception:
        pass
    try:
        # last resort: mutate attribute
        out.details = details
        return out
    except Exception:
        return out


def _suggest_best_same_side_limit(side: str, meta: dict):
    """Suggest TAIFEX MWP best_same_side_limit from best bid/ask in meta.

    Conservative mapping (交易所語義一致):
      - BUY  -> best ask
      - SELL -> best bid

    Accepts multiple common key names to minimize integration friction.
    Returns (suggested_value, source_key) or (None, None).
    """
    if not meta:
        return None, None
    s = str(side or "").strip().upper()

    ask_keys = ("ask", "best_ask", "ask_price", "best_offer", "offer", "offer_price")
    bid_keys = ("bid", "best_bid", "bid_price", "best_bid_price")

    def pick(keys):
        for k in keys:
            if k in meta and meta.get(k) is not None:
                try:
                    return float(meta.get(k)), k
                except Exception:
                    pass
        return None, None

    if s in ("BUY", "B"):
        return pick(bid_keys)
    if s in ("SELL", "S"):
        return pick(ask_keys)
    return None, None



def guard_order_v1(
    *,
    symbol: Optional[str] = None,
    code: Optional[str] = None,
    side: Optional[str] = None,
    order_type: str,
    qty: float,
    price: Optional[float] = None,
    meta: Optional[Dict[str, Any]] = None,
    now=None,
) -> OrderGuardVerdict:
    """Primary OrderGuard entrypoint (v1).

    Current v18.1 scope:
    - TAIFEX preflight hard gate (order-size limits, MWP same-side anchor, DPB/DPBM regime block)
    Future v18.1+:
    - price-limit proximity / dynamic protection regimes (more granular)
    - symbol/product specific limits (TX/MTX/TMF subsets first)
    - additional broker validation (Shioaji field-level constraints)
    """

    # --- broker field-level hard gate (Shioaji): MKT/MKP must use IOC ---
    # Shioaji docs/QA: MKT,MKP only accept IOC order_type (TIF). Caller should pass tif via meta.
    _meta = dict(meta or {})
    tif = _extract_tif(_meta)
    ot = _normalize_price_type_to_ot(order_type)
    if tif and ot in {"MARKET", "MWP"} and tif != "IOC":
        return OrderGuardVerdict(
            ok=False,
            code="EXEC_TIF_UNSUPPORTED_FOR_MKT_MKP",
            reason=f"Shioaji requires tif=IOC for {ot} (got tif={tif})",
            details={
                "tif": tif,
                "ot": ot,
                "hint": "Use meta.tif='IOC' (Shioaji MKT/MKP only accept IOC).",
            },
        )
    v = check_taifex_preflight(
        symbol=symbol,
        code=code,
        side=side,
        order_type=order_type,
        qty=qty,
        price=price,
        now=now,
        meta=meta,
    )
    out = OrderGuardVerdict.from_preflight(v)

    # --- enrich MWP missing same-side anchor with suggested_meta (no auto-mutation) ---
    try:
        if (not v.ok) and getattr(v, "code", "") == "EXEC_TAIFEX_MWP_NO_SAMESIDE_LIMIT":
            _meta2 = dict(meta or {})
            sug, src_key = _suggest_best_same_side_limit(side, _meta2)
            d = dict(out.details or {})
            if sug is not None:
                d["suggested_meta"] = {"best_same_side_limit": sug}
                d["suggested_meta_source"] = src_key
                d["hint"] = "MWP requires best_same_side_limit; suggested from best-of-book in meta (BUY->ask, SELL->bid)."
            else:
                d.setdefault("hint", "MWP requires best_same_side_limit. Provide meta.ask/best_ask (BUY) or meta.bid/best_bid (SELL).")
            # OrderGuardVerdict is a NamedTuple in this project; use _replace if available.
            out = _with_details(out, d)
    except Exception:
        pass

    return out


def get_scaffold_info() -> Dict[str, Any]:
    # Keep compatibility for any old callers/tests expecting this function.
    return {
        "module": "execution/order_guard.py",
        "status": "IMPLEMENTED",
        "v": "v18.1_mvp",
        "public": ["guard_order_v1", "OrderGuardVerdict", "get_scaffold_info"],
    }


__all__ = ["guard_order_v1", "OrderGuardVerdict", "get_scaffold_info"]
