from __future__ import annotations

import hashlib
import json
import platform
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

@dataclass
class ReplayResult:
    ok: bool
    code: str
    reason: str
    details: Dict[str, Any]

def _iso_to_epoch(ts: Optional[str]) -> Optional[float]:
    if not ts or not isinstance(ts, str):
        return None
    s = ts.strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    except Exception:
        return None

def _to_int(x: Any) -> Optional[int]:
    try:
        if x is None:
            return None
        if isinstance(x, bool):
            return int(x)
        if isinstance(x, int):
            return int(x)
        if isinstance(x, float):
            return int(x)
        if isinstance(x, str) and x.strip().isdigit():
            return int(x.strip())
        return None
    except Exception:
        return None

def _event_sort_key(ev: Dict[str, Any], line_no: int) -> Tuple[float, int, str, int]:
    # OFFICIAL-LOCKED deterministic ordering (best-effort):
    # 1) timestamp-like field (epoch; missing -> 0)
    # 2) sequence-like field (seq/event_id/id/rowid/offset; missing -> line_no)
    # 3) kind
    # 4) original line_no (stable tie-break)
    ts = None
    for k in ("ts", "event_ts", "ingest_ts", "recv_ts", "time"):
        if k in ev:
            ts = ev.get(k)
            break
    te = _iso_to_epoch(ts)
    if te is None:
        te = 0.0

    seq = None
    for k in ("seq", "event_id", "id", "rowid", "offset"):
        if k in ev:
            seq = ev.get(k)
            break
    si = _to_int(seq)
    if si is None:
        si = int(line_no)

    kind = ev.get("kind")
    kind_s = kind if isinstance(kind, str) else ""

    return (float(te), int(si), kind_s, int(line_no))

def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def _sha256_events(events: Iterable[Dict[str, Any]]) -> str:
    h = hashlib.sha256()
    for ev in events:
        b = json.dumps(ev, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        h.update(b)
        h.update(b"\n")
    return h.hexdigest()

def _write_report(report_json: Optional[Path], report_md: Optional[Path], payload: Dict[str, Any]) -> None:
    # OFFICIAL-LOCKED: avoid f-string dict-key NameError by never using payload.get(KEY) without quotes.
    if report_json:
        report_json.parent.mkdir(parents=True, exist_ok=True)
        report_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if report_md:
        report_md.parent.mkdir(parents=True, exist_ok=True)
        lines = []
        lines.append("# TMF AutoTrader — Replay Report")
        lines.append("- generated: {}".format(payload.get("generated_at")))
        lines.append("- log_path: `{}`".format(payload.get("log_path")))
        lines.append("- log_sha256: `{}`".format(payload.get("log_sha256")))
        lines.append("- deterministic: `{}`".format(payload.get("deterministic")))
        lines.append("- replayed: `{}`".format(payload.get("replayed")))
        lines.append("- bad: `{}`".format(payload.get("bad")))
        lines.append("- events_sha256: `{}`".format(payload.get("events_sha256")))
        lines.append("")
        lines.append("## Kind sequence (head/tail)")
        lines.append("```")
        lines.append("head10=" + ",".join(payload.get("kinds_head10", [])))
        lines.append("tail10=" + ",".join(payload.get("kinds_tail10", [])))
        lines.append("```")
        report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
def replay_jsonl(
    log_path: str,
    handler: Callable[[Dict[str, Any]], None],
    *,
    deterministic: bool = True,
    report_json_path: Optional[str] = None,
    report_md_path: Optional[str] = None,
) -> ReplayResult:
    """
    Replay JSONL audit log. Each line must be a JSON object.

    OFFICIAL-LOCKED enhancements:
    - Deterministic ordering (best-effort) to reduce replay drift risk.
    - Optional artifacted replay report (JSON/MD) for evidence-chain + drift investigation.
    """
    p = Path(log_path)
    if not p.exists():
        return ReplayResult(False, "REPLAY_LOG_MISSING", "log path missing", {"log_path": str(p)})

    report_json = Path(report_json_path) if report_json_path else None
    report_md = Path(report_md_path) if report_md_path else None

    parsed: List[Tuple[Tuple[float, int, str, int], int, Dict[str, Any]]] = []
    bad = 0
    line_no = 0

    with p.open("r", encoding="utf-8") as f:
        for raw in f:
            line_no += 1
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if not isinstance(obj, dict):
                    bad += 1
                    continue
                k = _event_sort_key(obj, line_no)
                parsed.append((k, line_no, obj))
            except Exception:
                bad += 1

    if deterministic:
        parsed.sort(key=lambda t: t[0])

    events = [ev for _, __, ev in parsed]

    n = 0
    kinds: List[str] = []
    for ev in events:
        handler(ev)
        n += 1
        k = ev.get("kind")
        if isinstance(k, str):
            kinds.append(k)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "log_path": str(p),
        "log_sha256": _sha256_file(p),
        "deterministic": bool(deterministic),
        "replayed": int(n),
        "bad": int(bad),
        "events_sha256": _sha256_events(events),
        "kinds_head10": kinds[:10],
        "kinds_tail10": kinds[-10:],
        "python": platform.python_version(),
        "platform": platform.platform(),
        "notes": {
            "ordering_key": "ts/event_ts/ingest_ts/recv_ts/time + seq/event_id/id/rowid/offset + kind + line_no",
        },
    }
    # --- OFFICIAL-LOCKED: drift taxonomy + ordering diagnostics (best-effort, side-effect free) ---\n    missing_ts = 0\n    missing_seq = 0\n    kind_counts = {}\n    key_head5 = []\n    key_tail5 = []\n    for idx, (k, ln_no, ev) in enumerate(parsed):\n        te, si, ks, lno = k\n        if te == 0.0:\n            missing_ts += 1\n        if si == int(lno):\n            missing_seq += 1\n        kind_counts[ks] = kind_counts.get(ks, 0) + 1\n        if idx < 5:\n            key_head5.append({"k": [te, si, ks, lno], "line_no": ln_no})\n    for idx, (k, ln_no, ev) in enumerate(parsed[-5:]):\n        te, si, ks, lno = k\n        key_tail5.append({"k": [te, si, ks, lno], "line_no": ln_no})\n    total = max(1, len(parsed))\n    missing_ts_ratio = missing_ts / total\n    missing_seq_ratio = missing_seq / total\n    drift_codes = []\n    if bad > 0:\n        drift_codes.append("DRIFT_PARSE_ERRORS")\n    if missing_ts_ratio >= 0.5:\n        drift_codes.append("DRIFT_MISSING_TS_HIGH")\n    elif missing_ts_ratio > 0:\n        drift_codes.append("DRIFT_MISSING_TS_SOME")\n    if missing_seq_ratio >= 0.5:\n        drift_codes.append("DRIFT_MISSING_SEQ_HIGH")\n    elif missing_seq_ratio > 0:\n        drift_codes.append("DRIFT_MISSING_SEQ_SOME")\n    payload["diagnostics"] = {\n        "missing_ts": int(missing_ts),\n        "missing_seq": int(missing_seq),\n        "missing_ts_ratio": float(missing_ts_ratio),\n        "missing_seq_ratio": float(missing_seq_ratio),\n        "kind_counts": kind_counts,\n        "sort_key_head5": key_head5,\n        "sort_key_tail5": key_tail5,\n    }\n    payload["drift_codes"] = drift_codes\n    # --- end diagnostics ---\n    _write_report(report_json, report_md, payload)

    if bad > 0:
        return ReplayResult(
            False,
            "REPLAY_PARSE_ERRORS",
            "one or more lines failed to parse",
            {"replayed": n, "bad": bad, "log_path": str(p), "events_sha256": payload["events_sha256"]},
        )

    return ReplayResult(
        True,
        "OK",
        "replay ok",
        {"replayed": n, "bad": bad, "log_path": str(p), "events_sha256": payload["events_sha256"]},
    )
