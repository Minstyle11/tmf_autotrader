#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OPS: PROJECT_BOARD ULTRA Repair v1 (idempotent)

Guarantees:
- Removes any stray "[TASK:M8-" outside AUTO_PATCH_TASKS block.
- Canonicalizes legacy wrapper: exactly one pair wrapping the patch block.
- Removes legacy marker duplicates elsewhere.
- Removes obvious ghost duplicated patch sections after END (until next major section).
- Always writes a backup before modifying.
- After repair, runs HardGate + pm_refresh_board_and_verify.sh.

Exit codes:
- 0: OK (already clean or repaired)
- 2: FATAL (missing board/markers or cannot repair safely)
"""
from __future__ import annotations
from pathlib import Path
import re, sys, subprocess, datetime

BOARD = Path("docs/board/PROJECT_BOARD.md")

BEGIN = "<!-- AUTO_PATCH_TASKS_START -->"
END   = "<!-- AUTO_PATCH_TASKS_END -->"
LEG_BEGIN = "<!-- AUTO:PATCH_TASKS_BEGIN -->"
LEG_END   = "<!-- AUTO:PATCH_TASKS_END -->"

def fail(msg: str, code: int = 2) -> None:
    print(f"[FATAL][BOARD_REPAIR] {msg}", file=sys.stderr)
    raise SystemExit(code)

def backup(text: str) -> Path:
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    bak = BOARD.with_suffix(BOARD.suffix + f".bak_ULTRA_BOARD_REPAIR_{ts}")
    bak.write_text(text, encoding="utf-8")
    print(f"[OK] backup: {bak}")
    return bak

def ensure_patch_markers(s: str) -> str:
    if BEGIN in s and END in s:
        return s
    fail("missing AUTO_PATCH_TASKS_START/END markers (cannot repair)")

def strip_all_legacy_markers(s: str) -> str:
    return s.replace(LEG_BEGIN, "").replace(LEG_END, "")

rx_m8 = re.compile(r"^\\s*[-*+]\\s*\\[[ xX~!]\\]\\s*\\[TASK:M8-[^\\]]+\\].*$")

def strip_stray_m8_outside_patch_block(s: str) -> tuple[str,int]:
    s = ensure_patch_markers(s)
    b = s.find(BEGIN)
    e = s.find(END, b + 1)
    if b < 0 or e < 0 or e <= b:
        fail("patch markers out of order")
    e2 = e + len(END)

    pre = s[:b]
    blk = s[b:e2]
    post = s[e2:]

    removed = 0
    def scrub(chunk: str) -> str:
        nonlocal removed
        out=[]
        for ln in chunk.splitlines(True):
            if rx_m8.match(ln):
                removed += 1
                continue
            out.append(ln)
        return "".join(out)

    return scrub(pre) + blk + scrub(post), removed

def strip_ghost_after_end(s: str) -> tuple[str,bool]:
    # remove duplicated patch/task chunks after END (common drift)
    s = ensure_patch_markers(s)
    epos = s.find(END)
    tail = s[epos+len(END):]
    if ("[TASK:M8-" not in tail) and ("Patch-to-Tasks" not in tail) and ("Compliance Tasks (AUTO)" not in tail) and ("### vv18" not in tail):
        return s, False
    m0 = re.search(r"(?m)^(##\\s+v18\\.|##\\s+v18\\.x|###\\s+v+18_)", tail)
    if not m0:
        return s, False
    start = epos + len(END) + m0.start()
    m1 = re.search(r"(?m)^##\\s+(Always-On Bibles|Progress Log|AUTOLOG|里程碑完成度)\\b", tail[m0.start():])
    end = start + (m1.start() if m1 else len(tail)-m0.start())
    return (s[:start] + "\\n" + s[end:]), True

def canonicalize_wrapper(s: str) -> str:
    s = ensure_patch_markers(s)
    # remove all legacy markers then rewrap exactly once around the patch block
    s = strip_all_legacy_markers(s)
    b = s.find(BEGIN)
    e = s.find(END, b + 1)
    if b < 0 or e < 0 or e <= b:
        fail("patch markers invalid after legacy strip")
    e2 = e + len(END)
    block = s[b:e2].strip("\\n")
    wrapped = LEG_BEGIN + "\\n" + block + "\\n" + LEG_END
    return s[:b] + wrapped + s[e2:]

def main() -> None:
    if not BOARD.exists():
        fail(f"missing board: {BOARD}")

    s0 = BOARD.read_text(encoding="utf-8", errors="replace")
    backup(s0)

    s = s0
    s = ensure_patch_markers(s)
    s, ghost_cut = strip_ghost_after_end(s)
    s = canonicalize_wrapper(s)
    s, removed = strip_stray_m8_outside_patch_block(s)

    if s != s0:
        BOARD.write_text(s, encoding="utf-8")
        print(f"[OK] repaired board: removed_stray_m8={removed} ghost_cut={ghost_cut}")
    else:
        print("[OK] board already clean")

    # Post-check: HardGate + pm_refresh
    subprocess.run(["python3", "scripts/board_ultra_hardgate_v1.py"], check=True)
    subprocess.run(["/bin/bash", "scripts/pm_refresh_board_and_verify.sh"], check=True)
    print("[PASS] repair -> hardgate -> pm_refresh all OK")

if __name__ == "__main__":
    main()
