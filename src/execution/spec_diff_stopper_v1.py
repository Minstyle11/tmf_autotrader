
from __future__ import annotations
from typing import Any, Dict, List, Tuple, Optional

def _is_num(x: Any) -> bool:
    try:
        float(x)
        return True
    except Exception:
        return False

def _is_str(x: Any) -> bool:
    return isinstance(x, str)

def _is_bool(x: Any) -> bool:
    return isinstance(x, bool)

def _is_list(x: Any) -> bool:
    return isinstance(x, (list, tuple))

def _list_all(xs: Any, pred) -> bool:
    if not _is_list(xs):
        return False
    return all(pred(v) for v in list(xs))

def _problems_prefix(prefix: str, probs: List[str]) -> List[str]:
    return [f"{prefix}{s}" for s in probs]

def validate_bidask_fop_v1(payload: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Hard schema guard for bidask_fop_v1 (OFFICIAL).

    Required keys:
      - code: str
      - bid_price: list[number]  (level-1 at index 0)
      - ask_price: list[number]
      - bid_volume: list[number]
      - ask_volume: list[number]
      - synthetic: bool
    Optional keys:
      - bid, ask: number (backward compat)
      - recv_ts, ingest_ts: str (preferred for freshness)
      - source_file: str
    """
    probs: List[str] = []
    if not isinstance(payload, dict):
        return False, ["payload_not_dict"]

    # required
    if not _is_str(payload.get("code", None)):
        probs.append("code_missing_or_not_str")

    for k in ("bid_price","ask_price","bid_volume","ask_volume"):
        v = payload.get(k, None)
        if not _is_list(v) or len(list(v)) < 1:
            probs.append(f"{k}_missing_or_empty_list")
        else:
            # prices must be numeric-ish; volumes numeric-ish
            if "price" in k:
                if not _list_all(v, _is_num):
                    probs.append(f"{k}_has_non_numeric")
            else:
                if not _list_all(v, _is_num):
                    probs.append(f"{k}_has_non_numeric")

    if "synthetic" not in payload or not _is_bool(payload.get("synthetic")):
        probs.append("synthetic_missing_or_not_bool")

    # optional scalar bid/ask (if present must be numeric)
    for k in ("bid","ask"):
        if k in payload and payload.get(k) is not None and (not _is_num(payload.get(k))):
            probs.append(f"{k}_present_but_not_numeric")

    # optional ts fields if present must be str
    for k in ("recv_ts","ingest_ts","source_file"):
        if k in payload and payload.get(k) is not None and (not _is_str(payload.get(k))):
            probs.append(f"{k}_present_but_not_str")

    return (len(probs) == 0), probs

def validate(kind: str, payload: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Dispatcher. Add more kinds as we lock specs."""
    k = str(kind)
    if k == "bidask_fop_v1":
        return validate_bidask_fop_v1(payload)
    # Unknown kinds: do not block (yet). Return OK.
    return True, []
