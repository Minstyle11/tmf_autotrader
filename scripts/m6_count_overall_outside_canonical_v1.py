#!/usr/bin/env python3
from pathlib import Path
import re

BOARD = Path("docs/board/PROJECT_BOARD.md")
AUTO_S = "<!-- AUTO_PROGRESS_START -->"
AUTO_E = "<!-- AUTO_PROGRESS_END -->"
pat = re.compile(r"^\*\*專案總完成度\s*/\s*Overall completion:\*\*")

lines = BOARD.read_text(encoding="utf-8", errors="replace").splitlines()
in_auto = False
cnt = 0
for line in lines:
    if AUTO_S in line:
        in_auto = True
        continue
    if AUTO_E in line:
        in_auto = False
        continue
    if (not in_auto) and pat.match(line.strip()):
        cnt += 1

print(cnt)
