from __future__ import annotations
from pathlib import Path
from datetime import datetime
import re
import sys

BOARD = Path("docs/board/PROJECT_BOARD.md")

DEPR_BEGIN = "<!-- AUTO_PROGRESS_START -->"
DEPR_END   = "<!-- AUTO_PROGRESS_END -->"
CAN_BEGIN  = "<!-- AUTO:PROGRESS_BEGIN -->"
CAN_END    = "<!-- AUTO:PROGRESS_END -->"

PAT_TASK = re.compile(r"^\s*[-*+]\s*(?:\[(?P<b>[ xX~!])\]|\((?P<p>[ xX~!])\))\s+\[TASK:[^\]]+\].*$", re.M)

def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def count_tasks(txt: str):
    total=done=doing=blocked=0
    for m in PAT_TASK.finditer(txt):
        total += 1
        c = (m.group("b") or m.group("p") or " ").strip().lower()
        if c == "x":
            done += 1
        elif c == "~":
            doing += 1
        elif c == "!":
            blocked += 1
    todo = max(0, total - done - doing - blocked)
    pct = (100.0 * done / total) if total else 0.0
    return total, done, doing, blocked, todo, pct

def main() -> int:
    if not BOARD.exists():
        print(f"[FATAL] missing {BOARD}", file=sys.stderr)
        return 2

    txt = BOARD.read_text(encoding="utf-8", errors="replace")

    # Anchor: keep body from the first "## 里程碑完成度" onward.
    # If missing, fallback to first occurrence of "# TMF AutoTrader Project Board".
    anchor = None
    m = re.search(r"(?m)^##\s+里程碑完成度\s*$", txt)
    if m:
        anchor = m.start()
    else:
        m2 = re.search(r"(?m)^#\s+TMF AutoTrader Project Board\s+\(OFFICIAL\)\s*$", txt)
        if m2:
            anchor = m2.start()
        else:
            # last resort: keep entire document after removing junk blocks, but still rewrite header
            anchor = 0

    body = txt[anchor:]

    # Remove any existing progress blocks anywhere in body/header (to ensure SINGLE blocks)
    def strip_block(s: str, begin: str, end: str) -> str:
        if begin not in s or end not in s:
            return s
        pat = re.compile(re.escape(begin) + r".*?" + re.escape(end) + r"[ \t]*\n*", re.S)
        # remove ALL occurrences
        while True:
            ns, n = pat.subn("", s, count=1)
            if n == 0:
                break
            s = ns
        return s

    body = strip_block(body, DEPR_BEGIN, DEPR_END)
    body = strip_block(body, CAN_BEGIN, CAN_END)

    # Count from TASK truth in the WHOLE original doc (tasks live in body)
    total, done, doing, blocked, todo, pct = count_tasks(txt)
    now = now_stamp()

    # Rebuild header deterministically
    header = []
    header.append("# 專案進度總覽（自動計算）")
    header.append("")
    header.append(DEPR_BEGIN)
    header.append(f"**專案總完成度 / Overall completion:** {pct:.1f}%（已完成 {done} / {total} 項；未完成 {todo + doing + blocked} 項）")
    header.append("")
    header.append(f"- done   : {done}")
    header.append(f"- doing  : {doing}")
    header.append(f"- blocked: {blocked}")
    header.append(f"- todo   : {todo}")
    header.append(f"- invalid_like: 0")
    header.append(DEPR_END)
    # Required: exactly ONE Overall completion line OUTSIDE canonical AUTO_PROGRESS block (for M6 verifier)
    header.append(f"**專案總完成度 / Overall completion:** {pct:.1f}%（已完成 {done} / {total} 項；未完成 {todo + doing + blocked} 項）")
    header.append("")
    header.append(f"- 更新時間：{now}")
    header.append(f"- 專案總完成度：{pct:.1f}% （已完成 {done} / {total} 項；TODO {todo} / DOING {doing} / BLOCKED {blocked}）")
    header.append("")
    header.append(CAN_BEGIN)
    header.append(f"- **TOTAL:** {total}")
    header.append(f"- **TOTAL_TASKS:** {total}")
    header.append(f"- **TODO:** {todo}")
    header.append(f"- **DOING:** {doing}")
    header.append(f"- **DONE:** {done}")
    header.append(f"- **DONE_TASKS:** {done}")
    header.append(f"- **BLOCKED:** {blocked}")
    header.append(f"- **PCT:** {pct:.1f}%")
    header.append(f"- **LAST_BOARD_UPDATE_AT:** {now}")
    header.append(CAN_END)
    header.append("")

    new_txt = "\n".join(header) + body.lstrip("\n")

    # Final safety: eliminate any accidental literal \"\\n\" runs in the very beginning (junk prelude)
    # (If such junk exists, it is always before the H1; we already rebuilt from H1, so just in case:)
    if new_txt.startswith("<!-- AUTO_PROGRESS_START -->\\\\n"):
        # Convert escaped sequences to real newlines (should not happen after rebuild, but guard anyway)
        new_txt = new_txt.replace("\\\\n", "\n")

    BOARD.write_text(new_txt, encoding="utf-8")

    print(f"[OK] rebuilt header+blocks from TASK-truth: total={total} done={done} doing={doing} blocked={blocked} pct={pct:.1f}% now={now}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
