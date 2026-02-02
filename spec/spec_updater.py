from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, Optional

from spec.spec_diff_stopper import stop_if_diff

def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")

def load_json(p: Path) -> Dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))

def write_json(p: Path, obj: Dict[str, Any]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\\n", encoding="utf-8")

def ensure_minimal_spec_shape(spec: Dict[str, Any]) -> Dict[str, Any]:
    # Minimal schema: keep flexible; we only require top-level dict
    if not isinstance(spec, dict):
        raise ValueError("spec must be a JSON object (dict)")
    spec.setdefault("_meta", {})
    spec["_meta"].setdefault("generated_ts", _now_iso())
    return spec

def apply_candidate_as_canonical(canonical_path: Path, candidate_path: Path, snapshot_dir: Path) -> Path:
    canonical = load_json(canonical_path)
    candidate = load_json(candidate_path)
    canonical = ensure_minimal_spec_shape(canonical)
    candidate = ensure_minimal_spec_shape(candidate)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    snap = snapshot_dir / f"taifex_spec_canonical_before_{ts}.json"
    write_json(snap, canonical)

    write_json(canonical_path, candidate)
    return snap

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--canonical", default="spec/canonical/taifex_spec_v1.json")
    ap.add_argument("--candidate", default="runtime/spec/taifex_spec_latest.json")
    ap.add_argument("--mode", choices=["check", "apply"], default="check")
    ap.add_argument("--report", default="snapshots/spec_diff/spec_diff_report_latest.md")
    args = ap.parse_args()

    canonical_path = Path(args.canonical)
    candidate_path = Path(args.candidate)
    canonical_path.parent.mkdir(parents=True, exist_ok=True)

    # If canonical missing, seed with candidate (first bootstrap) but still record report
    if not canonical_path.exists():
        if not candidate_path.exists():
            raise SystemExit("[spec-updater] MISS both canonical and candidate; provide runtime/spec/taifex_spec_latest.json")
        apply_candidate_as_canonical(canonical_path, candidate_path, Path("snapshots/spec_diff"))
        ok, res = stop_if_diff(str(canonical_path), str(candidate_path), args.report)
        print("[spec-updater] BOOTSTRAP canonical from candidate; diff same=", ok, "report=", res.report_path)
        raise SystemExit(0)

    if not candidate_path.exists():
        raise SystemExit("[spec-updater] MISS candidate runtime/spec/taifex_spec_latest.json (fetch step not implemented yet)")

    ok, res = stop_if_diff(str(canonical_path), str(candidate_path), args.report)
    if ok:
        print("[spec-updater] OK no diff; report=", res.report_path)
        raise SystemExit(0)

    print("[spec-updater] DIFF detected; report=", res.report_path)
    if args.mode == "check":
        raise SystemExit(2)

    snap = apply_candidate_as_canonical(canonical_path, candidate_path, Path("snapshots/spec_diff"))
    print("[spec-updater] APPLIED candidate->canonical; backup=", snap)
    raise SystemExit(0)

if __name__ == "__main__":
    main()
