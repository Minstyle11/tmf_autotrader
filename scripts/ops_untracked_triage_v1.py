from __future__ import annotations
from pathlib import Path
from datetime import datetime
import subprocess, re

OUTDIR = Path("runtime/handoff/state")
OUTDIR.mkdir(parents=True, exist_ok=True)

def sh(cmd: list[str]) -> str:
    return subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT)

def git_untracked() -> list[str]:
    # porcelain: "?? path"
    out = sh(["git", "status", "--porcelain", "-uall"])
    paths = []
    for line in out.splitlines():
        if line.startswith("?? "):
            paths.append(line[3:])
    return paths

def bucket(p: str) -> str:
    s = p.strip()

    # ultra-suspicious artifacts (weird filenames / pollution)
    if any(k in s for k in [
        "SUSPECT_RENAMED__", "comma_echo", "[INFO] smoke override", "\\necho", "\necho"
    ]):
        return "C_QUARANTINE"

    # local machine / launchd: needs governance decision
    if s.startswith("LaunchAgents/") or s.startswith("repo/LaunchAgents/"):
        return "D_MANUAL"

    # outputs / caches / temp (default ignore)
    if s.startswith(("runtime/", "data/", "sandbox/")):
        return "B_GITIGNORE"

    # project modules: likely real work, but still safe to propose
    if s.startswith(("src/", "execution/", "scripts/")):
        return "A_GITADD"

    if s.startswith("ops/"):
        # code under ops is likely legit, directories like incidents/observability may be policy-defined → manual
        return "A_GITADD" if s.endswith(".py") else "D_MANUAL"

    if s.startswith(("docs/", "research/", "portfolio/", "risk/")):
        # docs may be legit; _inbox is usually raw
        if s.startswith("docs/_inbox/"):
            return "D_MANUAL"
        return "A_GITADD"

    return "D_MANUAL"

def main():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    paths = git_untracked()

    groups = {"A_GITADD": [], "B_GITIGNORE": [], "C_QUARANTINE": [], "D_MANUAL": []}
    for p in paths:
        groups[bucket(p)].append(p)

    def md_list(xs: list[str]) -> str:
        return "\n".join([f"- `{x}`" for x in xs]) if xs else "(none)"

    report = []
    report.append("# Untracked Triage Plan (SAFE, NO-DELETE)\n")
    report.append(f"- generated_at: {datetime.now().isoformat(timespec='seconds')}\n")
    report.append(f"- untracked_count: {len(paths)}\n")

    report.append("\n## A) 建議納管 git add（看起來像新功能/模組/腳本）\n\n")
    report.append(md_list(groups["A_GITADD"]) + "\n")

    report.append("\n## B) 建議加入 .gitignore（輸出/暫存/本機環境檔）\n\n")
    report.append(md_list(groups["B_GITIGNORE"]) + "\n")

    report.append("\n## C) 建議隔離（可疑檔名/污染 artefacts；已或應移入 quarantine）\n\n")
    report.append(md_list(groups["C_QUARANTINE"]) + "\n")

    report.append("\n## D) 需人工判讀（可能是新模組，也可能是本機/臨時）\n\n")
    report.append(md_list(groups["D_MANUAL"]) + "\n")

    out_path = OUTDIR / f"untracked_triage_plan_{ts}.md"
    out_latest = OUTDIR / "untracked_triage_plan_latest.md"
    out_path.write_text("".join(report), encoding="utf-8")
    out_latest.write_text("".join(report), encoding="utf-8")
    print(f"[OK] triage plan: {out_path}")
    print(f"[OK] triage latest: {out_latest}")
    print("[程序完成]")

if __name__ == "__main__":
    main()
