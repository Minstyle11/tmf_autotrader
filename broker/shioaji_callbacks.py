from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

DPBM_KEYWORDS = (
    "Dynamic Price Banding", "dynamic price banding", "DPBM",
    "動態價格穩定措施", "動態價格區間", "動態價格", "穩定措施",
)

def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")

def _safe_obj_to_dict(x: Any) -> Any:
    if x is None:
        return None
    if isinstance(x, (str, int, float, bool)):
        return x
    if isinstance(x, dict):
        return {str(k): _safe_obj_to_dict(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_safe_obj_to_dict(v) for v in x]
    for attr in ("_asdict", "asdict", "dict"):
        if hasattr(x, attr):
            try:
                m = getattr(x, attr)
                d = m() if callable(m) else m
                if isinstance(d, dict):
                    return _safe_obj_to_dict(d)
            except Exception:
                pass
    if hasattr(x, "__dict__"):
        try:
            return _safe_obj_to_dict(vars(x))
        except Exception:
            pass
    try:
        return {"_repr": repr(x)}
    except Exception:
        return {"_repr": "<unrepr>"}

def _contains_dpbm(text: str) -> bool:
    t = (text or "")
    return any(k in t for k in DPBM_KEYWORDS)

def classify_exec_reject(stat: Any, msg: Any) -> Tuple[Optional[str], Dict[str, Any]]:
    details: Dict[str, Any] = {}
    s = str(stat) if stat is not None else ""
    m = _safe_obj_to_dict(msg)

    try:
        blob = json.dumps(m, ensure_ascii=False)
    except Exception:
        blob = repr(m)

    is_reject = False
    for token in ("REJECT", "Rejected", "reject", "失敗", "拒", "錯誤", "Error", "FAIL"):
        if token in s or token in blob:
            is_reject = True
            break

    if not is_reject:
        return (None, {})

    if _contains_dpbm(blob):
        details["hint"] = "keyword_match"
        return ("EXEC_TAIFEX_DPBM_REJECT", details)

    return ("EXEC_TAIFEX_REJECT_GENERIC", details)

def write_order_event_jsonl(*, stat: Any, msg: Any, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    p = out_dir / f"shioaji_order_events.{ts}.jsonl"
    obj = {
        "ts": _now_iso(),
        "kind": "order_cb_v1",
        "payload": {"stat": str(stat), "msg": _safe_obj_to_dict(msg)},
    }
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")
    return p

@dataclass(frozen=True)
class OrderCallbackResult:
    ok: bool
    exec_code: Optional[str]
    details: Dict[str, Any]
    raw_path: Optional[str] = None

def make_order_callback(*, out_dir: Path):
    def _cb(stat: Any, msg: Any) -> None:
        p = write_order_event_jsonl(stat=stat, msg=msg, out_dir=out_dir)
        exec_code, details = classify_exec_reject(stat, msg)
        if exec_code:
            print(f"[ORDER_CB][REJECT] exec_code={exec_code} raw={p}")
        else:
            print(f"[ORDER_CB] raw={p}")
    return _cb
