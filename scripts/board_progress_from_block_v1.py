#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
import re

BOARD = Path("docs/board/PROJECT_BOARD.md")
AUTO_START = "<!-- AUTO_PROGRESS_START -->"
AUTO_END   = "<!-- AUTO_PROGRESS_END -->"

def _fatal(msg: str):
    raise SystemExit(f"[FATAL] {msg}")

def _extract_block(text: str) -> str:
    if AUTO_START not in text or AUTO_END not in text:
        _fatal("missing AUTO_PROGRESS markers in PROJECT_BOARD.md")
    a = text.index(AUTO_START) + len(AUTO_START)
    b = text.index(AUTO_END)
    return text[a:b]

def _find_int(pattern: str, block: str, key: str) -> int:
    m = re.search(pattern, block, flags=re.IGNORECASE | re.M)
    if not m:
        _fatal(f"cannot parse {key} from AUTO_PROGRESS block")
    return int(m.group(1))

def main():
    if not BOARD.exists():
        _fatal(f"missing board: {BOARD}")
    txt = BOARD.read_text(encoding="utf-8", errors="replace")
    block = _extract_block(txt)

    done   = _find_int(r"^\s*-\s*done\s*:\s*(\d+)\s*$", block, "done")
    doing  = _find_int(r"^\s*-\s*doing\s*:\s*(\d+)\s*$", block, "doing")
    blocked= _find_int(r"^\s*-\s*blocked\s*:\s*(\d+)\s*$", block, "blocked")
    todo   = _find_int(r"^\s*-\s*todo\s*:\s*(\d+)\s*$", block, "todo")
    inv    = _find_int(r"^\s*-\s*invalid_like\s*:\s*(\d+)\s*$", block, "invalid_like")

    total = done + doing + blocked + todo
    pct = (done / total * 100.0) if total else 0.0

    # ONE stable canonical log line for LaunchAgent logs
    print(f"[OK] canonical board progress: pct={pct:.1f}% done={done} total={total} doing={doing} blocked={blocked} todo={todo} invalid_like={inv}")

if __name__ == "__main__":
    main()
