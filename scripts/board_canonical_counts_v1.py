#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "docs/board/PROJECT_BOARD.md"

AUTO_START = "<!-- AUTO_PROGRESS_START -->"
AUTO_END   = "<!-- AUTO_PROGRESS_END -->"

@dataclass
class Counts:
    total: int = 0
    done: int = 0
    doing: int = 0
    blocked: int = 0
    todo: int = 0
    invalid_like: int = 0

def _is_fence(line: str) -> bool:
    return line.lstrip().startswith("```")

def _maybe_task_line(line: str) -> bool:
    s = line.lstrip()
    if not s:
        return False
    if s[0] not in "-*+":
        return False
    return ("[" in s and "]" in s)

def _parse_task(line: str):
    s = line.lstrip()
    if not s or s[0] not in "-*+":
        return (False, None)
    try:
        i = s.index("[")
        j = s.index("]", i + 1)
    except ValueError:
        return (False, None)
    if i > 4:
        return (False, None)
    box = s[i + 1 : j].strip()
    title = s[j + 1 :].strip()
    if not title:
        return (False, None)

    ch = box[:1] if box else " "
    if ch in ("x", "X"):
        return (True, "done")
    if ch == "~":
        return (True, "doing")
    if ch == "!":
        return (True, "blocked")
    if ch == "" or ch == " ":
        return (True, "todo")
    return (False, None)

def canonical_count(text: str) -> Counts:
    c = Counts()
    in_code = False
    in_auto = False

    for raw in text.splitlines():
        line = raw.rstrip("\n")

        if _is_fence(line):
            in_code = not in_code
            continue
        if in_code:
            continue

        if AUTO_START in line:
            in_auto = True
            continue
        if AUTO_END in line:
            in_auto = False
            continue
        if in_auto:
            continue

        if not _maybe_task_line(line):
            continue

        ok, st = _parse_task(line)
        if not ok:
            c.invalid_like += 1
            continue

        c.total += 1
        if st == "done":
            c.done += 1
        elif st == "doing":
            c.doing += 1
        elif st == "blocked":
            c.blocked += 1
        elif st == "todo":
            c.todo += 1

    return c

def main():
    if not BOARD.exists():
        raise SystemExit(f"[FATAL] missing board: {BOARD}")
    txt = BOARD.read_text(encoding="utf-8", errors="replace")
    c = canonical_count(txt)
    pct = (c.done / c.total * 100.0) if c.total else 0.0
    print(
        "[OK] canonical board progress: "
        f"pct={pct:.1f}% done={c.done} total={c.total} "
        f"doing={c.doing} blocked={c.blocked} todo={c.todo} invalid_like={c.invalid_like}"
    )

if __name__ == "__main__":
    main()
