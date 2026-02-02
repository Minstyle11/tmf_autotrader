from __future__ import annotations
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

@dataclass
class AuditEvent:
    ts: str
    kind: str
    payload: Dict[str, Any]

def _now() -> str:
    return datetime.now().isoformat(timespec="milliseconds")

def append_event(log_path: str, kind: str, payload: Dict[str, Any], ts: Optional[str] = None) -> str:
    """
    Append one audit event as JSONL. Returns the timestamp used.
    JSONL schema:
      {"ts": "...", "kind": "...", "payload": {...}}
    """
    p = Path(log_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    t = ts or _now()
    ev = {"ts": t, "kind": str(kind), "payload": payload if isinstance(payload, dict) else {"payload": payload}}
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(ev, ensure_ascii=False, separators=(",", ":")) + "\n")
    return t
