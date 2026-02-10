from __future__ import annotations
from pathlib import Path
import re
from datetime import datetime

BOARD = Path("docs/board/PROJECT_BOARD.md")

BEGIN = "<!-- AUTO:PROGRESS_BEGIN -->"
END   = "<!-- AUTO:PROGRESS_END -->"


def _compute_progress_from_block(board_txt: str):
    """
    Single Source of Truth:
    Parse AUTO:PROGRESS block and use it to drive header/legacy completion lines.
    """
    m_total = re.search(r'^\s*-\s*\*\*TOTAL_TASKS:\*\*\s*([0-9]+)\s*$', board_txt, flags=re.M)
    m_done  = re.search(r'^\s*-\s*\*\*DONE_TASKS:\*\*\s*([0-9]+)\s*$', board_txt, flags=re.M)
    if not (m_total and m_done):
        return None
    total = int(m_total.group(1))
    done  = int(m_done.group(1))
    open_ = max(0, total - done)
    pct = (100.0 * done / total) if total > 0 else 0.0
    return done, total, open_, pct


def _update_header_and_legacy(board_txt: str) -> str:
    now = _now_stamp()
    prog = _compute_progress_from_block(board_txt)
    if not prog:
        # If AUTO:PROGRESS is missing, do not touch header to avoid lying.
        return board_txt

    done, total, open_, pct = prog
    header_updated_at = f"- 更新時間：{now}"
    header_completion = f"- 專案總完成度：{pct:.1f}% （已完成 {done} / {total} 項）"
    legacy = f"**專案總完成度 / Overall completion:** {pct:.1f}%（已完成 {done} / {total} 項；未完成 {open_} 項）"

    lines = board_txt.splitlines(True)
    out = []
    saw_updated = False
    saw_completion = False
    inserted_legacy = False

    # Update header lines + keep structure stable
    for line in lines:
        if re.match(r'^\s*-\s*更新時間：', line):
            out.append(header_updated_at + "\n")
            saw_updated = True
            continue
        if re.match(r'^\s*-\s*專案總完成度：', line):
            out.append(header_completion + "\n")
            saw_completion = True
            continue
        out.append(line)

    # Ensure header exists (insert after first H1)
    if not (saw_updated and saw_completion):
        rebuilt = []
        inserted = False
        for line in out:
            rebuilt.append(line)
            if (not inserted) and line.startswith("# "):
                # after H1 line, insert missing header lines in canonical order
                if not saw_updated:
                    rebuilt.append(header_updated_at + "\n")
                if not saw_completion:
                    rebuilt.append(header_completion + "\n")
                inserted = True
        out = rebuilt

    board_txt = "".join(out)

    # Update legacy line if present; else insert once right after the header section
    if re.search(r'^\*\*專案總完成度\s*/\s*Overall completion:\*\*.*$', board_txt, flags=re.M):
        board_txt = re.sub(
            r'^\*\*專案總完成度\s*/\s*Overall completion:\*\*.*$',
            legacy,
            board_txt,
            flags=re.M
        )
        return board_txt

    # Insert legacy line once: after the header block (after "- 專案總完成度：" line)
    lines = board_txt.splitlines(True)
    out = []
    for line in lines:
        out.append(line)
        if (not inserted_legacy) and re.match(r'^\s*-\s*專案總完成度：', line):
            out.append("\n" + legacy + "\n\n")
            inserted_legacy = True
    return "".join(out)
def _now_stamp() -> str:
    # Asia/Taipei local time is fine for project board stamp
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _count_tasks(txt: str):
    # Count markdown task list items: - [ ] / - [x] (case-insensitive)
    total = 0
    done = 0
    for m in re.finditer(r'^\s*[-*]\s*\[(.| )\]\s+.*$', txt, flags=re.M):
        total += 1
        c = (m.group(1) or "").strip().lower()
        if c == "x":
            done += 1
    pct = (100.0 * done / total) if total else 0.0
    return total, done, pct

def _replace_progress_block(txt: str, *, total: int, done: int, pct: float) -> str:
    block = [
        BEGIN + "\n",
        f"- **TOTAL_TASKS:** {total}\n",
        f"- **DONE_TASKS:** {done}\n",
        f"- **PCT:** {pct:.1f}%\n",
        END + "\n",
    ]
    newblk = "".join(block)

    if BEGIN in txt and END in txt:
        # Replace between markers (inclusive)
        pat = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END) + r"\n?", flags=re.S)
        return pat.sub(newblk, txt, count=1)

    # If missing markers, insert near the top after "專案總完成度" line if possible, else after first H1.
    lines = txt.splitlines(True)
    out = []
    inserted = False
    for line in lines:
        out.append(line)
        if (not inserted) and re.match(r'^\s*-\s*專案總完成度：', line):
            out.append(newblk + "\n")
            inserted = True
    if not inserted:
        # insert after first H1
        m = re.search(r'^(#\s+.*\n)', txt, flags=re.M)
        if m:
            return re.sub(r'^(#\s+.*\n)', r'\1\n' + newblk + r'\n', txt, count=1, flags=re.M)
        return newblk + "\n" + txt
    return "".join(out)

def _update_timestamp_line(txt: str) -> str:
    # Update "更新時間：" line if present; otherwise insert under first H1.
    stamp = _now_stamp()
    if re.search(r'^\s*-\s*更新時間：', txt, flags=re.M):
        return re.sub(r'^\s*-\s*更新時間：.*$', f"- 更新時間：{stamp}", txt, count=1, flags=re.M)

    # Insert under first H1
    m = re.search(r'^(#\s+.*\n)', txt, flags=re.M)
    if m:
        return re.sub(r'^(#\s+.*\n)', r'\1' + f"- 更新時間：{stamp}\n", txt, count=1, flags=re.M)
    return f"- 更新時間：{stamp}\n" + txt

def main():
    if not BOARD.exists():
        raise SystemExit(f"[FATAL] missing {BOARD}")

    txt = BOARD.read_text(encoding="utf-8", errors="replace")
    total, done, pct = _count_tasks(txt)

    txt2 = _replace_progress_block(txt, total=total, done=done, pct=pct)
    txt2 = _update_timestamp_line(txt2)
    txt2 = _update_header_and_legacy(txt2)

    BOARD.write_text(txt2, encoding="utf-8")

if __name__ == "__main__":
    main()

### CANONICAL_SYNC_V1 ###
try:
 import subprocess,sys
 subprocess.run([sys.executable, "scripts/update_project_board_progress_v1.py"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
except Exception:
 pass

try:
 _b=Path("docs/board/PROJECT_BOARD.md").read_text(encoding="utf-8",errors="replace").splitlines()
 for _l in _b[:80]:
  if "專案總完成度" in _l and "已完成" in _l:
   print("[OK] canonical board progress:", _l.strip()); break
except Exception:
 pass
