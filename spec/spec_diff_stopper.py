from __future__ import annotations
import json
import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List

def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()

def _json_canon(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")

def _flatten_keys(obj: Any, prefix: str = "") -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            kk = f"{prefix}.{k}" if prefix else str(k)
            out.update(_flatten_keys(v, kk))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            kk = f"{prefix}[{i}]"
            out.update(_flatten_keys(v, kk))
    else:
        out[prefix] = obj
    return out

def _safe_load_json(p: Path) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Strict JSON loader for specs.
    v18 behavior: if candidate/canonical JSON cannot be parsed -> STOP (treated as diff) and must emit report.
    """
    try:
        txt = p.read_text(encoding="utf-8")
    except Exception as e:
        return None, f"read_error: {e}"
    try:
        obj = json.loads(txt)
        if not isinstance(obj, dict):
            return None, "json_root_not_object"
        return obj, None
    except Exception as e:
        # Provide short context without dumping huge file
        snippet = txt[:600].replace("\\n", "\\\\n")
        return None, f"json_parse_error: {e} | head600={snippet}"

@dataclass
class SpecDiffResult:
    same: bool
    sha_old: str
    sha_new: str
    changed_keys: List[str]
    report_path: Optional[str] = None
    err: Optional[str] = None

def diff_specs(old_spec: Dict[str, Any], new_spec: Dict[str, Any]) -> SpecDiffResult:
    sha_old = _sha256_bytes(_json_canon(old_spec))
    sha_new = _sha256_bytes(_json_canon(new_spec))
    if sha_old == sha_new:
        return SpecDiffResult(True, sha_old, sha_new, [])
    a = _flatten_keys(old_spec)
    b = _flatten_keys(new_spec)
    keys = sorted(set(a.keys()) | set(b.keys()))
    changed = [k for k in keys if a.get(k) != b.get(k)]
    return SpecDiffResult(False, sha_old, sha_new, changed)

def stop_if_diff(canonical_path: str, candidate_path: str, out_report: str) -> Tuple[bool, SpecDiffResult]:
    cp = Path(canonical_path)
    np = Path(candidate_path)
    rp = Path(out_report)
    rp.parent.mkdir(parents=True, exist_ok=True)

    old, err_old = _safe_load_json(cp)
    new, err_new = _safe_load_json(np)

    # Any parse/read error -> STOP (same=False) with report
    if err_old or err_new or old is None or new is None:
        res = SpecDiffResult(
            same=False,
            sha_old=("PARSE_ERROR" if err_old else _sha256_bytes(_json_canon(old or {}))),
            sha_new=("PARSE_ERROR" if err_new else _sha256_bytes(_json_canon(new or {}))),
            changed_keys=[],
            err=("; ".join([e for e in [err_old, err_new] if e]) or "unknown_error"),
        )
        lines = []
        lines.append("# SPEC DIFF STOPPER REPORT (v1)")
        lines.append("")
        lines.append(f"- canonical: {cp}")
        lines.append(f"- candidate: {np}")
        lines.append(f"- sha_old: {res.sha_old}")
        lines.append(f"- sha_new: {res.sha_new}")
        lines.append(f"- same: {res.same}")
        lines.append(f"- err: {res.err}")
        rp.write_text("\\n".join(lines) + "\\n", encoding="utf-8")
        res.report_path = str(rp)
        return (False, res)

    res = diff_specs(old, new)

    lines = []
    lines.append("# SPEC DIFF STOPPER REPORT (v1)")
    lines.append("")
    lines.append(f"- canonical: {cp}")
    lines.append(f"- candidate: {np}")
    lines.append(f"- sha_old: {res.sha_old}")
    lines.append(f"- sha_new: {res.sha_new}")
    lines.append(f"- same: {res.same}")
    lines.append(f"- changed_keys_count: {len(res.changed_keys)}")
    lines.append("")
    if not res.same:
        lines.append("## Changed keys (top 200)")
        for k in res.changed_keys[:200]:
            lines.append(f"- {k}")
        if len(res.changed_keys) > 200:
            lines.append(f"- ... ({len(res.changed_keys)-200} more)")
    rp.write_text("\\n".join(lines) + "\\n", encoding="utf-8")
    res.report_path = str(rp)

    return (res.same, res)

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--canonical", required=True)
    ap.add_argument("--candidate", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    ok, res = stop_if_diff(args.canonical, args.candidate, args.out)
    print(f"[spec-diff] same={ok} sha_old={res.sha_old[:10]} sha_new={res.sha_new[:10]} changed={len(res.changed_keys)} report={res.report_path} err={res.err}")
    raise SystemExit(0 if ok else 2)
