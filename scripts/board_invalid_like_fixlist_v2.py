#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PROJECT_BOARD invalid_like fixlist generator (v2 - canonical, no-regex, no-anchors)
- Reads docs/board/PROJECT_BOARD.md
- Parses markdown task list items robustly (GFM-like: - [ ] / - [x] / - [~] / - [!])
- Ignores fenced code blocks ```...```
- Ignores AUTO_PROGRESS region (<!-- AUTO_PROGRESS_START --> ... <!-- AUTO_PROGRESS_END -->)
- Emits a fixlist markdown under runtime/handoff/state/
Output is stable and does NOT depend on source-code anchors.
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
    """
    Return (ok, state, title, reason)
    ok=True => canonical task
    state in {"done","doing","blocked","todo"}
    """
    s = line.lstrip()
    if not s or s[0] not in "-*+":
        return (False, None, None, "not a bullet")
    # require bullet + space
    if len(s) < 3 or s[1] != " ":
        return (False, None, None, "missing space after bullet")
    try:
        i = s.index("[")
        j = s.index("]", i + 1)
    except ValueError:
        return (False, None, None, "missing [ ]")
    if i > 4:
        return (False, None, None, "checkbox too far from bullet")
    box = s[i + 1 : j].strip()
    title = s[j + 1 :].strip()
    if not title:
        return (False, None, None, "missing title")
    ch = box[:1] if box else " "
    if ch in ("x", "X"):
        return (True, "done", title, "")
    if ch == "~":
        return (True, "doing", title, "")
    if ch == "!":
        return (True, "blocked", title, "")
    if ch == "" or ch == " ":
        return (True, "todo", title, "")
    return (False, None, None, f"unknown checkbox char: {repr(ch)}")

def scan(text: str):
    c = Counts()
    invalid = []
    in_code = False
    in_auto = False
    for idx, raw in enumerate(text.splitlines(), start=1):
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

        ok, st, title, reason = _parse_task(line)
        if not ok:
            c.invalid_like += 1
            invalid.append((idx, line, reason))
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
    return c, invalid

def main():
    if not BOARD.exists():
        raise SystemExit(f"[FATAL] missing board: {BOARD}")
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    txt = BOARD.read_text(encoding="utf-8", errors="replace")
    c, invalid = scan(txt)

    ts = time.strftime("%Y%m%d_%H%M%S")
    outp = STATE_DIR / f"PROJECT_BOARD_INVALID_LIKE_FIXLIST_{ts}.md"
    with outp.open("w", encoding="utf-8") as f:
        f.write("# PROJECT_BOARD invalid_like fixlist (v2)\n\n")
        f.write(f"- board: {BOARD}\n")
        f.write(f"- generated: {ts}\n\n")
        f.write("## Summary\n\n")
        f.write(f"- total_tasks: {c.total}\n")
        f.write(f"- done: {c.done}\n")
        f.write(f"- doing: {c.doing}\n")
        f.write(f"- blocked: {c.blocked}\n")
        f.write(f"- todo: {c.todo}\n")
        f.write(f"- invalid_like: {c.invalid_like}\n\n")

        if not invalid:
            f.write("## invalid_like lines\n\n- (none)\n")
        else:
            f.write("## invalid_like lines (line_no | reason | content)\n\n")
            for ln, content, reason in invalid:
                f.write(f"- L{ln} | {reason} | `{content}`\n")

            f.write("\n## Recommended fix policy\n\n")
            f.write("1) 任何要當 task 的行，統一改成：`- [ ] 標題` / `- [x] 標題` / `- [~] 標題` / `- [!] 標題`\n")
            f.write("2) bullet 後面一定要有一個空白（`-␠[ ]`）\n")
            f.write("3) checkbox 後面一定要有標題文字\n")

    print(f"[OK] wrote fixlist(v2): {outp}")
    print(f"[OK] invalid_like_count={c.invalid_like} total={c.total} done={c.done} doing={c.doing} blocked={c.blocked} todo={c.todo}")

if __name__ == "__main__":
    main()
