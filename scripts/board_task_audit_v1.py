#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PROJECT_BOARD canonical task audit (v1) — NO regex.
Canonical task line:
  bullet (-/*/+), spaces, [state], space, title
state in: " ", x, X, ~, !
Skips:
- fenced code blocks
- AUTO_PROGRESS region (between markers)
Writes audit report under runtime/handoff/state/
"""
from __future__ import annotations
from pathlib import Path
from datetime import datetime

STATE_CHARS = {" ", "x", "X", "~", "!"}
BULLETS = {"-", "*", "+"}
AUTO_BEGIN = "<!-- AUTO_PROGRESS:BEGIN -->"
AUTO_END   = "<!-- AUTO_PROGRESS:END -->"

def _is_fence(line: str) -> bool:
    s = line.lstrip()
    return s.startswith("```") or s.startswith("~~~")

def parse_board(text: str):
    in_code = False
    in_auto = False
    items = []
    invalid_like = []

    for idx, raw in enumerate(text.splitlines(), start=1):
        line = raw.rstrip("\n")
        if line.startswith("\ufeff"):
            line = line[1:]

        if _is_fence(line):
            in_code = not in_code
            continue
        if in_code:
            continue

        if AUTO_BEGIN in line:
            in_auto = True
            continue
        if AUTO_END in line:
            in_auto = False
            continue
        if in_auto:
            continue

        s = line.lstrip()
        if not s:
            continue

        if s[0] not in BULLETS:
            if ("[ ]" in s) or ("[x]" in s.lower()) or ("[~]" in s) or ("[!]" in s):
                invalid_like.append((idx, line))
            continue

        j = 1
        while j < len(s) and s[j] == " ":
            j += 1
        if j >= len(s) or s[j] != "[":
            continue
        if j + 2 >= len(s):
            continue
        st = s[j + 1]
        if st not in STATE_CHARS:
            continue
        if s[j + 2] != "]":
            continue
        if j + 3 >= len(s) or s[j + 3] != " ":
            continue
        title = s[j + 4:].strip()
        if not title:
            continue

        items.append((idx, st, title, line))

    total = len(items)
    done = sum(1 for _, st, *_ in items if st in ("x", "X"))
    doing = sum(1 for _, st, *_ in items if st == "~")
    blocked = sum(1 for _, st, *_ in items if st == "!")
    todo = total - done - doing - blocked
    pct = (done / total * 100.0) if total else 0.0

    # dup titles
    seen = {}
    dups = []
    for idx, st, title, line in items:
        k = title.strip()
        seen.setdefault(k, []).append((idx, st, line))
    for k, arr in seen.items():
        if len(arr) > 1:
            dups.append((k, arr))

    return {
        "total": total, "done": done, "doing": doing, "blocked": blocked, "todo": todo, "pct": pct,
        "items": items, "invalid_like": invalid_like, "dup_titles": dups,
    }

def write_audit(board_path: Path, out_dir: Path) -> Path:
    text = board_path.read_text(encoding="utf-8", errors="replace")
    r = parse_board(text)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = out_dir / f"PROJECT_BOARD_CANONICAL_TASK_AUDIT_{ts}.md"

    lines = []
    lines.append("# PROJECT_BOARD Canonical Task Audit (v1)\n")
    lines.append(f"- board: `{board_path}`")
    lines.append(f"- timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
