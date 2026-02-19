#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PROJECT_BOARD progress updater (v2 - canonical, checkbox-only)
- Ignore fenced code blocks ```...```
- Ignore AUTO_PROGRESS region (if markers exist)
- ONLY treat canonical checkbox tasks as tasks:
    - [ ] / [x]/[X] / [~] / [!]
  i.e. lines like "- [2026-02-11] ..." are NOT tasks and will be ignored.
- Writes canonical audit to runtime/handoff/state/
"""
from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass
import time

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "docs/board/PROJECT_BOARD.md"
STATE_DIR = ROOT / "runtime/handoff/state"

AUTO_START = "<!-- AUTO_PROGRESS_START -->"
AUTO_END   = "<!-- AUTO_PROGRESS_END -->"

ALLOWED_BOX = {"", " ", "x", "X", "~", "!"}

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
    """
    Checkbox-only fast filter:
      starts with bullet (-/*/+) then space then [ then one char then ] then space
    Accepts:
      - [ ] title
      - [x] title
      - [~] title
      - [!] title
    """
    s = line.lstrip()
    if len(s) < 6:
        return False
    if s[0] not in "-*+":
        return False
    if s[1] != " ":
        return False
    if s[2] != "[":
        return False
    # s[3] is checkbox char (may be space)
    if s[4] != "]":
        return False
    if s[5] != " ":
        return False
    return True

def _parse_task(line: str):
    """
    Return (is_task, state, title, is_invalid_like)
    - is_task True: canonical checkbox task
    - is_task False & is_invalid_like False: not a task
    - is_task False & is_invalid_like True : looks like task but malformed (should be fixed)
    """
    s = line.lstrip()
    if not s or s[0] not in "-*+":
        return (False, None, None, False)

    # strict checkbox-only pattern at fixed positions
    if not _maybe_task_line(s):
        return (False, None, None, False)

    box = s[3]  # single char
    if box not in {" ", "x", "X", "~", "!"}:
        # Should never happen due to _maybe_task_line, but keep as invalid-like
        return (False, None, None, True)

    title = s[6:].strip()
    if not title:
        return (False, None, None, True)

    if box in ("x", "X"):
        return (True, "done", title, False)
    if box == "~":
        return (True, "doing", title, False)
    if box == "!":
        return (True, "blocked", title, False)
    return (True, "todo", title, False)

def canonical_count(lines: list[str]) -> tuple[Counts, list[str]]:
    c = Counts()
    audit_lines = []
    in_code = False
    in_auto = False

    for raw in lines:
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

        is_task, st, _title, invalid_like = _parse_task(line)
        if not is_task:
            if invalid_like:
                c.invalid_like += 1
                audit_lines.append(f"[INVALID_LIKE] {line}")
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

    return c, audit_lines

def _render_auto_progress(c: Counts) -> str:
    pct = (c.done / c.total * 100.0) if c.total else 0.0
    return (
        f"{AUTO_START}\n"
        f"**專案總完成度 / Overall completion:** {pct:.1f}%（已完成 {c.done} / {c.total} 項；未完成 {c.total - c.done} 項）\n\n"
        f"- done   : {c.done}\n"
        f"- doing  : {c.doing}\n"
        f"- blocked: {c.blocked}\n"
        f"- todo   : {c.todo}\n"
        f"- invalid_like: {c.invalid_like}\n"
        f"{AUTO_END}\n"
    )

def _insert_or_replace_progress(text: str, block: str) -> str:
    if AUTO_START in text and AUTO_END in text:
        a = text.index(AUTO_START)
        b = text.index(AUTO_END) + len(AUTO_END)
        return text[:a].rstrip() + "\n\n" + block + "\n" + text[b:].lstrip()

    # no markers: insert after first heading if any, else prepend
    lines = text.splitlines(True)
    out = []
    inserted = False
    for ln in lines:
        out.append(ln)
        if not inserted and ln.startswith("#"):
            out.append("\n")
            out.append(block)
            out.append("\n")
            inserted = True
    if not inserted:
        return block + "\n" + text
    return "".join(out)

def main():
    if not BOARD.exists():
        raise SystemExit(f"[FATAL] missing board: {BOARD}")

    STATE_DIR.mkdir(parents=True, exist_ok=True)

    text = BOARD.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines(True)

    c, audit = canonical_count(lines)

    ts = time.strftime("%Y%m%d_%H%M%S")
    audit_path = STATE_DIR / f"PROJECT_BOARD_CANONICAL_TASK_AUDIT_{ts}.md"
    with audit_path.open("w", encoding="utf-8") as f:
        f.write("=== [CANONICAL AUDIT / CHECKBOX-ONLY] ===\n")
        f.write(f"board={BOARD}\n")
        f.write(f"total={c.total} done={c.done} doing={c.doing} blocked={c.blocked} todo={c.todo}\n")
        f.write(f"invalid_like={c.invalid_like}\n\n")
        if audit:
            f.write("## invalid_like lines\n")
            for x in audit:
                f.write(x + "\n")

    block = _render_auto_progress(c)
    new_text = _insert_or_replace_progress(text, block)

    bak = BOARD.with_suffix(".md.bak_autofix_" + ts)
    bak.write_text(text, encoding="utf-8")
    BOARD.write_text(new_text, encoding="utf-8")

    pct = (c.done / c.total * 100.0) if c.total else 0.0
    print(f"[OK] PROJECT_BOARD recomputed (CANONICAL): total={c.total} done={c.done} doing={c.doing} blocked={c.blocked} todo={c.todo} pct={pct:.1f}% invalid_like={c.invalid_like}")
    print(f"[OK] canonical board progress: pct={pct:.1f}% done={c.done} total={c.total} doing={c.doing} blocked={c.blocked} todo={c.todo} invalid_like={c.invalid_like}")
    print(f"[OK] backup: {bak}")
    print(f"[OK] audit : {audit_path}")

if __name__ == "__main__":
    main()
