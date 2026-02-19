#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path

BOARD = Path("docs/board/PROJECT_BOARD.md")
AUTO_S = "<!-- AUTO_PROGRESS_START -->"
AUTO_E = "<!-- AUTO_PROGRESS_END -->"
TARGET = "**專案總完成度 / Overall completion:**"

def main():
    txt = BOARD.read_text(encoding="utf-8", errors="replace")
    # Count TARGET lines that appear OUTSIDE the canonical AUTO_PROGRESS_START/END block
    lines = txt.splitlines()
    in_auto = False
    cnt = 0
    for ln in lines:
        if AUTO_S in ln:
            in_auto = True
            continue
        if AUTO_E in ln:
            in_auto = False
            continue
        if in_auto:
            continue
        if TARGET in ln:
            cnt += 1
    print(cnt)

if __name__ == "__main__":
    main()
