#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
from pathlib import Path
from datetime import datetime
import re

BOARD = Path("docs/board/PROJECT_BOARD.md")

AUTO_S = "<!-- AUTO_PROGRESS_START -->"
AUTO_E = "<!-- AUTO_PROGRESS_END -->"

AP_BEGIN = "<!-- AUTO:PROGRESS_BEGIN -->"
AP_END   = "<!-- AUTO:PROGRESS_END -->"

def _fatal(msg: str):
    raise SystemExit(f"[FATAL] {msg}")

def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _extract_canonical_block(txt: str) -> str:
    if AUTO_S not in txt or AUTO_E not in txt:
        _fatal("missing canonical AUTO_PROGRESS_START/END block")
    a = txt.index(AUTO_S) + len(AUTO_S)
    b = txt.index(AUTO_E)
    return txt[a:b]

def _parse_counts(block: str):
    def _find(pat: str, key: str) -> int:
        m = re.search(pat, block, flags=re.IGNORECASE | re.M)
        if not m:
            _fatal(f"cannot parse {key} from canonical block")
        return int(m.group(1))

    done    = _find(r"^\s*-\s*done\s*:\s*(\d+)\s*$", "done")
    doing   = _find(r"^\s*-\s*doing\s*:\s*(\d+)\s*$", "doing")
    blocked = _find(r"^\s*-\s*blocked\s*:\s*(\d+)\s*$", "blocked")
    todo    = _find(r"^\s*-\s*todo\s*:\s*(\d+)\s*$", "todo")
    inv     = _find(r"^\s*-\s*invalid_like\s*:\s*(\d+)\s*$", "invalid_like")

    total = done + doing + blocked + todo
    open_ = total - done
    pct = (100.0 * done / total) if total else 0.0
    return done, total, open_, pct, doing, blocked, todo, inv

def _rewrite_auto_progress_begin_end(txt: str, *, total: int, done: int, doing: int, blocked: int, pct: float, stamp: str) -> str:
    newblk = (
        f"{AP_BEGIN}\n"
        f"- 更新時間：{stamp}\n"
        f"- **TOTAL_TASKS:** {total}\n"
        f"- **DONE_TASKS:** {done}\n"
        f"- **DOING_TASKS:** {doing}\n"
        f"- **BLOCKED_TASKS:** {blocked}\n"
        f"- **PCT:** {pct:.1f}%\n"
        f"{AP_END}\n"
    )
    if AP_BEGIN in txt and AP_END in txt:
        pat = re.compile(re.escape(AP_BEGIN) + r".*?" + re.escape(AP_END) + r"\n?", flags=re.S)
        return pat.sub(newblk, txt, count=1)
    # insert after header completion line if possible; else after first H1
    lines = txt.splitlines(True)
    out = []
    inserted = False
    for ln in lines:
        out.append(ln)
        if (not inserted) and re.match(r"^\s*-\s*專案總完成度：", ln):
            out.append("\n" + newblk + "\n")
            inserted = True
    if inserted:
        return "".join(out)
    m = re.search(r"^(#\s+.*\n)", txt, flags=re.M)
    if m:
        return re.sub(r"^(#\s+.*\n)", r"\1\n" + newblk + r"\n", txt, count=1, flags=re.M)
    return newblk + "\n" + txt

def _rewrite_header_and_legacy(txt: str, *, done: int, total: int, open_: int, pct: float, stamp: str) -> str:
    header_updated = f"- 更新時間：{stamp}"
    header_completion = f"- 專案總完成度：{pct:.1f}% （已完成 {done} / {total} 項）"
    legacy = f"**專案總完成度 / Overall completion:** {pct:.1f}%（已完成 {done} / {total} 項；未完成 {open_} 項）"

    lines = txt.splitlines(True)
    out = []
    saw_updated = False
    saw_completion = False

    for ln in lines:
        if re.match(r"^\s*-\s*更新時間：", ln):
            out.append(header_updated + "\n")
            saw_updated = True
            continue
        if re.match(r"^\s*-\s*專案總完成度：", ln):
            out.append(header_completion + "\n")
            saw_completion = True
            continue
        out.append(ln)

    txt2 = "".join(out)

    # ensure header lines exist under first H1
    if not (saw_updated and saw_completion):
        rebuilt = []
        inserted = False
        for ln in txt2.splitlines(True):
            rebuilt.append(ln)
            if (not inserted) and ln.startswith("# "):
                if not saw_updated:
                    rebuilt.append(header_updated + "\n")
                if not saw_completion:
                    rebuilt.append(header_completion + "\n")
                inserted = True
        txt2 = "".join(rebuilt)

    # update FIRST legacy line BEFORE AUTO_PROGRESS_START (never touch inside canonical block)
    cut = txt2.find(AUTO_S)
    prefix = txt2 if cut < 0 else txt2[:cut]
    suffix = "" if cut < 0 else txt2[cut:]

    if re.search(r"^\*\*專案總完成度\s*/\s*Overall completion:\*\*.*$", prefix, flags=re.M):
        prefix = re.sub(r"^\*\*專案總完成度\s*/\s*Overall completion:\*\*.*$", legacy, prefix, count=1, flags=re.M)
    else:
        # insert once right after completion line
        lines = prefix.splitlines(True)
        tmp = []
        inserted = False
        for ln in lines:
            tmp.append(ln)
            if (not inserted) and re.match(r"^\s*-\s*專案總完成度：", ln):
                tmp.append("\n" + legacy + "\n\n")
                inserted = True
        prefix = "".join(tmp)

    # de-dupe any extra legacy lines in prefix (keep first only)
    pref_lines = prefix.splitlines(True)
    kept = []
    seen = False
    for ln in pref_lines:
        if re.match(r"^\*\*專案總完成度\s*/\s*Overall completion:\*\*.*$", ln):
            if seen:
                continue
            seen = True
        kept.append(ln)
    prefix = "".join(kept)

    return prefix + suffix

def main():
    if not BOARD.exists():
        _fatal(f"missing board: {BOARD}")
    txt = BOARD.read_text(encoding="utf-8", errors="replace")
    block = _extract_canonical_block(txt)
    done, total, open_, pct, doing, blocked, todo, inv = _parse_counts(block)

    stamp = _now()
    txt2 = _rewrite_header_and_legacy(txt, done=done, total=total, open_=open_, pct=pct, stamp=stamp)
    txt2 = _rewrite_auto_progress_begin_end(txt2, total=total, done=done, doing=doing, blocked=blocked, pct=pct, stamp=stamp)

    BOARD.write_text(txt2, encoding="utf-8")
    print(f"[OK] synced PROJECT_BOARD head+AUTO:PROGRESS to canonical: done={done} total={total} doing={doing} blocked={blocked} todo={todo} pct={pct:.1f}% invalid_like={inv}")

if __name__ == "__main__":
    main()
