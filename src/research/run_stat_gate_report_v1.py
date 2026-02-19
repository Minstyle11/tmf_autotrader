"""
TMF AutoTrader — Stat Gate Report Runner v1
- Reads in-memory demo returns (for now)
- Produces: runtime/research/STAT_GATE_REPORT_latest.md (+ sha256)
            runtime/research/REPLAY_SEED_latest.yaml (+ sha256)
OFFICIAL-LOCKED compatible (no extra deps).
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import json, os, subprocess, random

from src.research.stat_gate_v1 import run_stat_gate_v1

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "runtime" / "research"

def _utc_ts() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def _sha256_file(p: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def _write_sidecar(p: Path) -> str:
    sha = _sha256_file(p)
    sidecar = p.with_name(p.name + ".sha256.txt")
    sidecar.write_text(f"{sha}  {p.name}\n", encoding="utf-8")
    return sha

def _git_head() -> str:
    try:
        r = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=str(ROOT), text=True).strip()
        return r
    except Exception:
        return "UNKNOWN"

def demo_returns() -> dict:
    # Deterministic demo: one mild positive edge + two noise (so gate can PASS/FAIL depending on thresholds)
    rng = random.Random(7)
    T = 1500
    s_edge = [rng.gauss(0.00035, 0.01) for _ in range(T)]
    s_n1   = [rng.gauss(0.0,     0.01) for _ in range(T)]
    s_n2   = [rng.gauss(0.0,     0.01) for _ in range(T)]
    return {"edge": s_edge, "noise1": s_n1, "noise2": s_n2}

def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    returns = demo_returns()
    n_trials = int(os.environ.get("TMF_STAT_N_TRIALS", "20"))
    pbo_max  = float(os.environ.get("TMF_STAT_PBO_MAX", "0.10"))
    dsr_min  = float(os.environ.get("TMF_STAT_DSR_MIN", "0.95"))
    ann_fac  = float(os.environ.get("TMF_STAT_ANN_FACTOR", "252"))

    res = run_stat_gate_v1(
        returns,
        pbo_max=pbo_max,
        dsr_min=dsr_min,
        n_trials=n_trials,
        ann_factor=ann_fac,
    )

    report = OUT_DIR / "STAT_GATE_REPORT_latest.md"
    seed   = OUT_DIR / "REPLAY_SEED_latest.yaml"

    ts = _utc_ts()
    head = _git_head()
    payload = {
        "ts_utc": ts,
        "git_head": head,
        "cfg": {
            "n_trials": n_trials,
            "pbo_max": pbo_max,
            "dsr_min": dsr_min,
            "ann_factor": ann_fac,
            "note": "demo_returns (deterministic) — replace with real research runner in next tasks",
        },
        "result": {
            "ok": res.ok,
            "code": res.code,
            "reason": res.reason,
            "details": res.details,
        },
    }

    report.write_text(
        "\n".join([
            "# STAT_GATE_REPORT (v1) — latest",
            f"- ts_utc: `{ts}`",
            f"- git_head: `{head}`",
            "",
            "## Config",
            "```json",
            json.dumps(payload["cfg"], ensure_ascii=False, indent=2),
            "```",
            "",
            "## Result",
            "```json",
            json.dumps(payload["result"], ensure_ascii=False, indent=2),
            "```",
            "",
            "## Notes",
            "- This is the minimal artifact runner. Next task will wire real strategy candidate returns + MODEL_CARD + full replay seed.",
            "",
        ]) + "\n",
        encoding="utf-8",
    )
    report_sha = _write_sidecar(report)

    seed.write_text(
        "\n".join([
            f"ts_utc: {ts}",
            f"git_head: {head}",
            "data_split: demo_returns_deterministic_v1",
            "random_seed: 7",
            "cost_model: taifex_fee_tax_v1",
            "stat_gate:",
            f"  n_trials: {n_trials}",
            f"  pbo_max: {pbo_max}",
            f"  dsr_min: {dsr_min}",
            f"  ann_factor: {ann_fac}",
            f"  result_code: {res.code}",
            f"  result_ok: {str(bool(res.ok)).lower()}",
        ]) + "\n",
        encoding="utf-8",
    )
    seed_sha = _write_sidecar(seed)

    print(f"[OK] wrote {report} sha256={report_sha}")
    print(f"[OK] wrote {seed} sha256={seed_sha}")
    print(f"[OK] result ok={res.ok} code={res.code} reason={res.reason}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
