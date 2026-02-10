#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re

BOARD_PATH = Path("docs/board/PROJECT_BOARD.md")
STATE_DIR = Path("runtime/handoff/state")
STATE_DIR.mkdir(parents=True, exist_ok=True)

AUTO_BEGIN = "<!-- AUTO:PROGRESS_BEGIN -->"
AUTO_END   = "<!-- AUTO:PROGRESS_END -->"

STRICT_RX = re.compile(r"^\s*(?:[-*+]|\d+\.)\s*\[\s*([xX~! ])\s*\]\s+(.+?)\s*$")
LOOSE_RX  = re.compile(r"^\s*[-*]\s*\[\s*([xX~! ])\s*\]\s*(.+?)\s*$")
LEGEND_RX = re.compile(r"^\s*-\s*\[[ xX~!]\]\s*(TODO|DOING|DONE|BLOCKED)\s*$", re.IGNORECASE)
FENCE_RX  = re.compile(r"^\s*```")

@dataclass(frozen=True)
class Counts:
    total: int
    done: int
    doing: int
    blocked: int

    @property
    def pct(self) -> float:
        return (self.done / self.total * 100.0) if self.total else 0.0

def classify(mark: str) -> str:
    m = mark.strip()
    if m.lower() == "x":
        return "done"
    if m == "~":
        return "doing"
    if m == "!":
        return "blocked"
    return "todo"

def scan(lines: list[str], rx: re.Pattern) -> tuple[Counts, list[tuple[int,str,str]]]:
    in_code = False
    total = done = doing = blocked = 0
    rows: list[tuple[int,str,str]] = []

    for idx, line in enumerate(lines, start=1):
        if FENCE_RX.match(line):
            in_code = not in_code
            continue
        if in_code:
            continue
        if LEGEND_RX.match(line):
            continue

        m = rx.match(line)
        if not m:
            continue

        mark = m.group(1)
        text = m.group(2).strip()
        kind = classify(mark)

        total += 1
        if kind == "done":
            done += 1
        elif kind == "doing":
            doing += 1
        elif kind == "blocked":
            blocked += 1

        rows.append((idx, mark, text))

    return Counts(total=total, done=done, doing=doing, blocked=blocked), rows

def replace_auto_block(s: str, c: Counts, now: str) -> str:
    block = (
        f"{AUTO_BEGIN}\n"
        f"- 更新時間：{now}\n"
        f"- **TOTAL_TASKS:** {c.total}\n"
        f"- **DONE_TASKS:** {c.done}\n"
        f"- **DOING_TASKS:** {c.doing}\n"
        f"- **BLOCKED_TASKS:** {c.blocked}\n"
        f"- **PCT:** {c.pct:.1f}%\n"
        f"{AUTO_END}"
    )

    if (AUTO_BEGIN in s) and (AUTO_END in s):
        return re.sub(re.escape(AUTO_BEGIN) + r".*?" + re.escape(AUTO_END), block, s, flags=re.S)

    return block + "\n\n" + s

def best_effort_sync_summary(s: str, c: Counts, now: str) -> str:
    s = re.sub(r"專案總完成度：\s*.*",
               f"專案總完成度：{c.pct:.1f}% （已完成 {c.done} / {c.total} 項）",
               s, count=1)
    s = re.sub(r"\*\*專案總完成度 / Overall completion:\*\*\s*.*",
               f"**專案總完成度 / Overall completion:** {c.pct:.1f}%（已完成 {c.done} / {c.total} 項；未完成 {c.total - c.done} 項）",
               s, count=1)
    s = re.sub(r"- 更新時間：\s*.*",
               f"- 更新時間：{now}",
               s, count=1)
    return s

def write_audit(ts: str,
                strict_rows: list[tuple[int,str,str]],
                loose_rows: list[tuple[int,str,str]],
                strict_c: Counts,
                loose_c: Counts) -> tuple[Path,Path,Path]:

    def dump(path: Path, title: str, c: Counts, rows) -> None:
        out = []
        out.append(f"# {title}\n\n")
        out.append(f"- time: {ts}\n")
        out.append(f"- total={c.total} done={c.done} doing={c.doing} blocked={c.blocked} pct={c.pct:.1f}%\n\n")
        out.append("| line | mark | text |\n|---:|:---:|---|\n")
        for ln, mk, tx in rows:
            out.append(f"| {ln} | `{mk}` | {tx} |\n")
        path.write_text("".join(out), encoding="utf-8")

    strict_path = STATE_DIR / f"PROJECT_BOARD_TASK_AUDIT_STRICT_{ts}.md"
    loose_path  = STATE_DIR / f"PROJECT_BOARD_TASK_AUDIT_LOOSE_{ts}.md"
    diff_path   = STATE_DIR / f"PROJECT_BOARD_TASK_AUDIT_DIFF_{ts}.md"

    dump(strict_path, "PROJECT_BOARD TASK AUDIT (STRICT)", strict_c, strict_rows)
    dump(loose_path,  "PROJECT_BOARD TASK AUDIT (LOOSE)",  loose_c,  loose_rows)

    strict_set = {(ln, tx) for ln, _, tx in strict_rows}
    missed = [(ln, mk, tx) for ln, mk, tx in loose_rows if (ln, tx) not in strict_set]

    out = []
    out.append("# PROJECT_BOARD TASK AUDIT DIFF (LOOSE minus STRICT)\n\n")
    out.append(f"- time: {ts}\n")
    out.append(f"- STRICT total={strict_c.total} done={strict_c.done} pct={strict_c.pct:.1f}%\n")
    out.append(f"- LOOSE  total={loose_c.total} done={loose_c.done} pct={loose_c.pct:.1f}%\n")
    out.append(f"- missed_by_strict={len(missed)}\n\n")
    out.append("| line | mark | text |\n|---:|:---:|---|\n")
    for ln, mk, tx in missed:
        out.append(f"| {ln} | `{mk}` | {tx} |\n")

    diff_path.write_text("".join(out), encoding="utf-8")
    return strict_path, loose_path, diff_path

def main() -> int:
    if not BOARD_PATH.exists():
        raise SystemExit(f"[FATAL] missing {BOARD_PATH}")

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    s = BOARD_PATH.read_text(encoding="utf-8", errors="replace")
    bk = BOARD_PATH.with_suffix(".md.bak_autofix_" + ts)
    bk.write_text(s, encoding="utf-8")

    lines = s.splitlines(True)

    strict_c, strict_rows = scan(lines, STRICT_RX)
    loose_c,  loose_rows  = scan(lines, LOOSE_RX)

    # Canonical: LOOSE (your requirement: ensure all items are counted)
    canonical = loose_c

    s2 = replace_auto_block(s, canonical, now)
    s2 = best_effort_sync_summary(s2, canonical, now)
    BOARD_PATH.write_text(s2, encoding="utf-8")

    strict_path, loose_path, diff_path = write_audit(ts, strict_rows, loose_rows, strict_c, loose_c)

    print(f"[OK] PROJECT_BOARD updated using LOOSE counting: total={canonical.total} done={canonical.done} doing={canonical.doing} blocked={canonical.blocked} pct={canonical.pct:.1f}%")
    print(f"[OK] backup: {bk}")
    print(f"[OK] audit(strict): {strict_path}")
    print(f"[OK] audit(loose) : {loose_path}")
    print(f"[OK] diff audit  : {diff_path}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
