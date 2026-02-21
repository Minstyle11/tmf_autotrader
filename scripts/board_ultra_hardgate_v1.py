#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PROJECT_BOARD ULTRA HardGate v1 (wrapper-aware, fail-fast)

Invariants:
1) Exactly one legacy wrapper pair exists:
   LEG_BEGIN < BEGIN < END < LEG_END
2) No legacy markers outside that wrapper.
3) No stray "[TASK:M8-" outside patch block (root cause of 576 explosion).
4) Patch block markers exist and are ordered.

FAIL -> exit 2 with [FAIL][BOARD_HARDGATE] reason.
"""
from __future__ import annotations
from pathlib import Path
import re, sys

BOARD = Path("docs/board/PROJECT_BOARD.md")

BEGIN = "<!-- AUTO_PATCH_TASKS_START -->"
END   = "<!-- AUTO_PATCH_TASKS_END -->"
LEG_BEGIN = "<!-- AUTO:PATCH_TASKS_BEGIN -->"
LEG_END   = "<!-- AUTO:PATCH_TASKS_END -->"

def fail(msg: str, code: int = 2) -> None:
    print(f"[FAIL][BOARD_HARDGATE] {msg}", file=sys.stderr)
    raise SystemExit(code)

def main() -> None:
    if not BOARD.exists():
        fail(f"missing board: {BOARD}")

    s = BOARD.read_text(encoding="utf-8", errors="replace")

    lb = [m.start() for m in re.finditer(re.escape(LEG_BEGIN), s)]
    le = [m.start() for m in re.finditer(re.escape(LEG_END), s)]
    if len(lb) != 1 or len(le) != 1:
        fail(f"legacy marker count invalid (LEG_BEGIN={len(lb)} LEG_END={len(le)})")

    b = s.find(BEGIN)
    e = s.find(END, b + 1)
    if b < 0:
        fail("missing AUTO_PATCH_TASKS_START")
    if e < 0:
        fail("missing AUTO_PATCH_TASKS_END")
    if e <= b:
        fail("AUTO_PATCH_TASKS markers out of order (END <= START)")

    if not (lb[0] < b < e < le[0]):
        fail("wrapper order invalid (expect LEG_BEGIN < BEGIN < END < LEG_END)")

    wrapper_start = lb[0]
    wrapper_end = le[0] + len(LEG_END)
    outside = s[:wrapper_start] + s[wrapper_end:]
    if (LEG_BEGIN in outside) or (LEG_END in outside):
        fail("legacy markers found outside canonical wrapper")

    # Root-cause guard: no stray M8 tasks outside patch block (use pure string check; no regex risk)
    pre = s[:b]
    post = s[e + len(END):]
    if "[TASK:M8-" in pre or "[TASK:M8-" in post:
        fail("FOUND stray [TASK:M8-] outside patch block")

    print("[PASS][BOARD_HARDGATE] OK")

if __name__ == "__main__":
    main()
