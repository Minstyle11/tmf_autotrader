from __future__ import annotations
import subprocess
import sys
import re
from pathlib import Path

BOARD = Path("docs/board/PROJECT_BOARD.md")

# Trust source: TASK checkbox lines only (never parse header blocks)
PAT_TASK = re.compile(
    r"^\s*[-*+]\s*(?:\[(?P<b>[ xX~!])\]|\((?P<p>[ xX~!])\))\s+\[TASK:[^\]]+\].*$",
    re.M,
)

def count_from_task_truth(txt: str):
    total=done=doing=blocked=0
    for m in PAT_TASK.finditer(txt):
        total += 1
        c = (m.group("b") or m.group("p") or " ").strip().lower()
        if c == "x":
            done += 1
        elif c == "~":
            doing += 1
        elif c == "!":
            blocked += 1
    todo = max(0, total - done - doing - blocked)
    pct = (100.0 * done / total) if total else 0.0
    return total, done, doing, blocked, todo, pct

def main() -> int:
    # Always rebuild header+blocks first (single-writer)
    r = subprocess.run([sys.executable, "scripts/board_rebuild_header_from_task_truth_v1.py"], capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr or "")
        sys.stderr.write(r.stdout or "")
        return r.returncode

    txt = BOARD.read_text(encoding="utf-8", errors="replace")
    total, done, doing, blocked, todo, pct = count_from_task_truth(txt)

    print(f"[OK] canonical board progress: - 專案總完成度：{pct:.1f}% （已完成 {done} / {total} 項）")
    print(f"[OK] counts: total={total} done={done} doing={doing} blocked={blocked} pct={pct:.1f}%")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
