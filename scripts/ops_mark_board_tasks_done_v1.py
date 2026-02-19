#!/usr/bin/env python3
from pathlib import Path
import sys

def main():
    board = Path("docs/board/PROJECT_BOARD.md")
    tasks = [t.strip() for t in sys.argv[1:] if t.strip()]
    if not tasks:
        raise SystemExit("[FATAL] no task ids provided")

    s = board.read_text(encoding="utf-8", errors="replace").splitlines(True)
    changed = 0
    for i, line in enumerate(s):
        for tid in tasks:
            if f"[TASK:{tid}]" in line and "- [ ]" in line:
                s[i] = line.replace("- [ ]", "- [x]", 1)
                changed += 1

    board.write_text("".join(s), encoding="utf-8")
    print(f"[OK] marked DONE: changed_lines={changed} tasks={len(tasks)} board={board}")

if __name__ == "__main__":
    main()
