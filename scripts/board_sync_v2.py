#!/usr/bin/env python3
from __future__ import annotations
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Tuple

BOARD_PATH = Path("docs/board/PROJECT_BOARD.md")

AUTO_START = "<!-- AUTO_BOARD_SYNC_START -->"
AUTO_END   = "<!-- AUTO_BOARD_SYNC_END -->"

# Only these exact patterns are forbidden OUTSIDE auto block.
FORBIDDEN_OUTSIDE = [
    re.compile(r"^\*\*專案總完成度 / Overall completion:\*\*"),
    re.compile(r"^- 專案總完成度：\s*\d+(\.\d+)?%"),
    re.compile(r"^- done\s*:"),
    re.compile(r"^- doing\s*:"),
    re.compile(r"^- blocked\s*:"),
    re.compile(r"^- todo\s*:"),
    re.compile(r"^- invalid_like\s*:"),
    re.compile(r"^<!-- AUTO_PROGRESS_START -->"),
    re.compile(r"^<!-- AUTO_PROGRESS_END -->"),
    re.compile(r"^<!-- AUTO:PROGRESS_BEGIN -->"),
    re.compile(r"^<!-- AUTO:PROGRESS_END -->"),
    re.compile(r"^- \*\*(TOTAL|TOTAL_TASKS|TODO|DOING|DONE|DONE_TASKS|BLOCKED|PCT|LAST_BOARD_UPDATE_AT):\*\*"),
]

TASK_RE = re.compile(r"^- \[(?P<st>[ x~!])\]\s+\[TASK:(?P<id>[^\]]+)\]\s+.+$")

@dataclass
class Stats:
    total: int
    done: int
    doing: int
    blocked: int
    todo: int
    invalid_like: int = 0

    @property
    def pct(self) -> float:
        return (self.done / self.total * 100.0) if self.total else 0.0

def parse_tasks(lines: List[str]) -> Stats:
    total=done=doing=blocked=todo=0
    for ln in lines:
        m = TASK_RE.match(ln)
        if not m:
            continue
        total += 1
        st = m.group("st")
        if st == "x":
            done += 1
        elif st == "~":
            doing += 1
        elif st == "!":
            blocked += 1
        else:
            todo += 1
    return Stats(total=total, done=done, doing=doing, blocked=blocked, todo=todo, invalid_like=0)

def render_auto_block(st: Stats) -> List[str]:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pct = f"{st.pct:.1f}"
    return [
        AUTO_START,
        f"**專案總完成度 / Overall completion:** {pct}%（已完成 {st.done} / {st.total} 項；未完成 {st.total - st.done} 項）",
        "",
        f"- done   : {st.done}",
        f"- doing  : {st.doing}",
        f"- blocked: {st.blocked}",
        f"- todo   : {st.todo}",
        f"- invalid_like: {st.invalid_like}",
        "",
        f"- 更新時間：{now}",
        AUTO_END,
    ]

def strip_forbidden_outside(lines: List[str]) -> Tuple[List[str], int]:
    out=[]
    removed=0
    in_auto=False
    for ln in lines:
        if ln.strip() == AUTO_START:
            in_auto=True
            out.append(ln)
            continue
        if ln.strip() == AUTO_END:
            in_auto=False
            out.append(ln)
            continue
        if not in_auto:
            s = ln.rstrip("\n")
            if any(p.match(s) for p in FORBIDDEN_OUTSIDE):
                removed += 1
                continue
        out.append(ln)
    return out, removed

def upsert_auto_block(lines: List[str], block: List[str]) -> List[str]:
    # Replace existing AUTO block if present; else insert near top after title line.
    try:
        i = next(i for i,ln in enumerate(lines) if ln.strip() == AUTO_START)
        j = next(i for i,ln in enumerate(lines) if ln.strip() == AUTO_END)
        if j <= i:
            raise StopIteration
        new = lines[:i] + [x+"\n" for x in block] + lines[j+1:]
        return new
    except StopIteration:
        # Insert after first H1 or first non-empty line
        insert_at = 0
        for idx, ln in enumerate(lines):
            if ln.startswith("# "):
                insert_at = idx+1
                break
        new = lines[:insert_at] + ["\n"] + [x+"\n" for x in block] + ["\n"] + lines[insert_at:]
        return new

def main():
    if not BOARD_PATH.exists():
        raise SystemExit(f"[FATAL] missing {BOARD_PATH}")
    raw = BOARD_PATH.read_text(encoding="utf-8")
    lines = raw.splitlines(True)

    # 1) Remove any legacy progress snippets outside AUTO block (precise patterns only)
    lines, removed = strip_forbidden_outside(lines)

    # 2) Recompute stats from TASK lines ONLY
    st = parse_tasks([ln.rstrip("\n") for ln in lines])
    if st.total <= 0:
        raise SystemExit("[FATAL] no TASK lines found; cannot compute progress")

    # 3) Upsert single authoritative AUTO block
    block = render_auto_block(st)
    lines = upsert_auto_block(lines, block)

    # Mode: sync or check
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--sync", action="store_true")
    args = ap.parse_args()

    new_text = "".join(lines)
    if args.check:
        if new_text != raw:
            raise SystemExit("[FATAL] PROJECT_BOARD out-of-sync: run `python3 scripts/board_sync_v2.py --sync`")
        print("[OK] PROJECT_BOARD in sync")
        return

    if not args.sync:
        args.sync = True

    if args.sync:
        # write back
        backup = BOARD_PATH.with_suffix(".md.bak_board_sync_v2")
        backup.write_text(raw, encoding="utf-8")
        BOARD_PATH.write_text(new_text, encoding="utf-8")
        print(f"[OK] board synced: {BOARD_PATH} (backup={backup}) removed_legacy={removed} total={st.total} done={st.done} pct={st.pct:.1f}%")

if __name__ == "__main__":
    main()
