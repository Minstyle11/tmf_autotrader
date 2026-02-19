from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable

def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")

def _iter_jsonl(paths: Iterable[Path]) -> Iterable[Dict[str, Any]]:
    for p in paths:
        if not p.exists():
            continue
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue

def build_reject_stats(*, events: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    total = 0
    rejects = 0
    by_exec_code: Dict[str, int] = {}
    samples: Dict[str, Any] = {}

    for e in events:
        total += 1
        payload = (e.get("payload") or {})
        stat = str(payload.get("stat") or "")
        msg  = payload.get("msg")

        try:
            blob = json.dumps(msg, ensure_ascii=False)
        except Exception:
            blob = repr(msg)

        is_reject = any(k in stat for k in ("REJECT","Rejected","reject","失敗","拒","Error","FAIL")) or \
                    any(k in blob for k in ("REJECT","Rejected","reject","失敗","拒","Error","FAIL"))

        if not is_reject:
            continue

        rejects += 1

        exec_code = None
        if isinstance(payload, dict):
            exec_code = payload.get("exec_code")
        if not exec_code:
            if any(k in blob for k in ("DPBM","Dynamic Price Banding","動態價格","穩定措施")):
                exec_code = "EXEC_TAIFEX_DPBM_REJECT"
            else:
                exec_code = "EXEC_TAIFEX_REJECT_GENERIC"

        by_exec_code[exec_code] = by_exec_code.get(exec_code, 0) + 1
        if exec_code not in samples:
            samples[exec_code] = {"stat": stat, "msg": msg}

    return {
        "generated_at": _now_iso(),
        "total_events": total,
        "reject_events": rejects,
        "reject_rate": (rejects / total) if total else 0.0,
        "by_exec_code": by_exec_code,
        "samples": samples,
    }

def main() -> int:
    raw_dir = Path("runtime/raw_events")
    paths_all = list(raw_dir.glob("shioaji_order_events.*.jsonl"))
    # Prefer REAL callback files; keep regtest only when it is the only choice.
    paths_real = [x for x in paths_all if not x.name.endswith(".regtest.jsonl")]
    paths = paths_real if paths_real else paths_all
    paths = sorted(paths, key=lambda x: x.stat().st_mtime)

    rep = build_reject_stats(events=_iter_jsonl(paths))

    out_json = Path("runtime/handoff/state/reject_stats_report_latest.json")
    out_json.write_text(json.dumps(rep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("[OK] wrote:", out_json)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
