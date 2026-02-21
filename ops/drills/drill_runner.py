"""
Drill OS (v18): run drills and emit DRILL_REPORT_YYYYMMDD_HHMMSS_{suite}.md/json (+sha256).
v1 scope (deliver M3-OS-3 baseline):
  - Deterministic drill runner (no external deps)
  - Runs a small chaos suite using existing regression scripts as executables
  - Produces artifacts under runtime/reports/drills/
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional
from pathlib import Path
import json, subprocess, hashlib, datetime, os


@dataclass(frozen=True)
class DrillResult:
    ok: bool
    name: str
    details: Dict[str, Any]


def _sha256_bytes(b: bytes) -> str:
    h = hashlib.sha256()
    h.update(b)
    return h.hexdigest()


def _write_sha256_sidecar(path: Path) -> Path:
    b = path.read_bytes()
    s = f"{_sha256_bytes(b)}  {path.name}\n"
    side = path.with_suffix(path.suffix + ".sha256.txt")
    side.write_text(s, encoding="utf-8")
    return side


def _run_cmd(cmd: str, env: Optional[Dict[str, str]] = None, timeout_sec: int = 600) -> Dict[str, Any]:
    e = os.environ.copy()
    if env:
        e.update({k: str(v) for k, v in env.items()})
    p = subprocess.run(
        cmd,
        shell=True,
        env=e,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout_sec,
        text=True,
    )
    return {"cmd": cmd, "rc": p.returncode, "out": p.stdout}


def run_drill_suite(*, suite: str = "chaos_v1", out_dir: str = "runtime/reports/drills") -> DrillResult:
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    outp = Path(out_dir)
    outp.mkdir(parents=True, exist_ok=True)
    md = outp / f"DRILL_{ts}_{suite}.md"
    js = outp / f"DRILL_{ts}_{suite}.json"

    steps = []
    steps.append(_run_cmd("bash scripts/m3_regression_audit_replay_os_v1.sh"))
    steps.append(_run_cmd("bash scripts/m2_regression_market_quality_gates_v1.sh"))
    steps.append(_run_cmd("bash scripts/m3_regression_cost_model_os_v1.sh"))

    ok = all(s["rc"] == 0 for s in steps)
    result = {"suite": suite, "ok": ok, "steps": steps}
    js.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = []
    lines.append(f"# DRILL REPORT {suite}")
    lines.append(f"- ts: {ts}")
    lines.append(f"- ok: {ok}")
    lines.append("")
    for i, s in enumerate(steps, 1):
        lines.append(f"## Step {i}")
        lines.append(f"- cmd: `{s[cmd]}`")
        lines.append(f"- rc: {s[rc]}")
        lines.append("")
        lines.append("```")
        lines.append(s["out"].rstrip("\n"))
        lines.append("```")
        lines.append("")
    md.write_text("\n".join(lines), encoding="utf-8")

    _write_sha256_sidecar(js)
    _write_sha256_sidecar(md)

    return DrillResult(ok=ok, name=suite, details={"md": str(md), "json": str(js)})


if __name__ == "__main__":
    r = run_drill_suite()
    print(f"[DRILL] ok={r.ok} suite={r.name}")
    print(f"[DRILL] md={r.details.get(\"md\")}")
    print(f"[DRILL] json={r.details.get(\"json\")}")
