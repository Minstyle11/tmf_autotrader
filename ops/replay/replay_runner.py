from __future__ import annotations
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional

@dataclass
class ReplayResult:
    ok: bool
    code: str
    reason: str
    details: Dict[str, Any]

def replay_jsonl(log_path: str, handler: Callable[[Dict[str, Any]], None]) -> ReplayResult:
    """
    Replay JSONL audit log. Each line must be a JSON object.
    """
    p = Path(log_path)
    if not p.exists():
        return ReplayResult(False, "REPLAY_LOG_MISSING", "log path missing", {"log_path": str(p)})

    n = 0
    bad = 0
    with p.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if not isinstance(obj, dict):
                    bad += 1
                    continue
                handler(obj)
                n += 1
            except Exception:
                bad += 1

    if bad > 0:
        return ReplayResult(False, "REPLAY_PARSE_ERRORS", "one or more lines failed to parse", {"replayed": n, "bad": bad, "log_path": str(p)})

    return ReplayResult(True, "OK", "replay ok", {"replayed": n, "bad": bad, "log_path": str(p)})
