#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
m8_update_board_from_patches_v1.py (robust rewrite)

Goal:
- Generate/refresh Patch-to-Tasks AUTO block in docs/board/PROJECT_BOARD.md
- Preserve existing checkbox states inside AUTO block
- Remove accidental legacy/duplicate patch-task blocks that leaked outside AUTO block
- Keep task volume bounded (avoid blowing up TOTAL tasks)

Markers (single source of truth):
  BEGIN = <!-- AUTO_PATCH_TASKS_START -->
  END   = <!-- AUTO_PATCH_TASKS_END -->
"""

from __future__ import annotations

import re
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple

BOARD = Path("docs/board/PROJECT_BOARD.md")
PATCHES = [
    Path("docs/bibles/TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18_1_PATCH.md"),
    Path("docs/bibles/TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18_2_PATCH.md"),
    # v18.3 可選：若存在就一起納入（但一樣有上限）
    Path("docs/bibles/TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18_3_PATCH.md"),
]

BEGIN = "<!-- AUTO_PATCH_TASKS_START -->"
END   = "<!-- AUTO_PATCH_TASKS_END -->"

# Legacy markers (we remove any residual blocks if found)
LEG_BEGIN = "<!-- AUTO:PATCH_TASKS_BEGIN -->"
LEG_END   = "<!-- AUTO:PATCH_TASKS_END -->"

# Hard cap per patch to prevent task explosion
MAX_TASKS_PER_PATCH = 30

# --- helpers ---

def _sid(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", errors="ignore")).hexdigest()[:8]

def _norm(s: str) -> str:
    s = s.replace("\u00a0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _parse_task_line_state(line: str) -> Optional[Tuple[str, str]]:
    """
    Parse markdown task line of form:
      - [x] [TASK:XXXXX] ...
      - [ ] [TASK:XXXXX] ...
      - [~] / [!]
    Return (tid, mark) where mark in {" ", "x", "~", "!"}
    """
    s = line.lstrip()
    if not s.startswith("- ["):
        return None
    if "[TASK:" not in s:
        return None

    i0 = s.find("[")
    i1 = s.find("]", i0 + 1)
    if i0 < 0 or i1 < 0:
        return None
    mark = s[i0 + 1 : i1].strip()
    if mark not in ("", "x", "X", "~", "!"):
        return None
    mark = "x" if mark in ("x", "X") else (mark if mark else " ")

    j0 = s.find("TASK:")
    j1 = s.find("]", j0)
    if j0 < 0 or j1 < 0:
        return None
    tid = s[j0 + 5 : j1].strip()
    if not tid:
        return None
    return (tid, mark)

def _extract_task_state_map_in_auto_block(board_text: str) -> Dict[str, str]:
    """
    Preserve existing checkbox states ONLY from our AUTO_PATCH_TASKS block.
    """
    b0 = board_text.find(BEGIN)
    b1 = board_text.find(END, b0 + 1)
    if b0 < 0 or b1 < 0 or b1 <= b0:
        return {}
    block = board_text[b0:b1].splitlines()
    out: Dict[str, str] = {}
    for ln in block:
        p = _parse_task_line_state(ln)
        if not p:
            continue
        tid, mark = p
        out[tid] = mark
    return out

def _ensure_markers(board_text: str) -> str:
    if BEGIN in board_text and END in board_text:
        return board_text
    # Try insert near v18.1 header; else append end
    m = re.search(r"^##\s+v18\.1.*$", board_text, flags=re.M)
    insert_at = m.end() if m else len(board_text)
    block = "\n\n" + BEGIN + "\n\n" + END + "\n"
    return board_text[:insert_at] + block + board_text[insert_at:]

def _extract_reqs(md: str) -> List[str]:
    """
    Conservative extraction to avoid explosion:
    - Use headings (##/###) that look like requirements
    - Use bullet lines with bold + keywords
    - Keep de-dup, cap to MAX_TASKS_PER_PATCH
    """
    out: List[str] = []
    bad_titles = {"patch", "overview", "scope", "changelog"}
    head_rx = re.compile(r"^(#{2,3})\s+(.*)$")
    list_rx = re.compile(r"^\s*[-*]\s+(.*)$")
    key_rx = re.compile(r"(必須|強制|硬擋|送單前|order|taifex|shioaji|drift|rollback|canary|regime|rejected)", re.I)

    for ln in md.splitlines():
        t = ln.strip()
        if not t:
            continue
        if t.startswith("```") or t.startswith(">"):
            continue

        mh = head_rx.match(t)
        if mh:
            title = _norm(mh.group(2).replace("**", ""))
            if not title:
                continue
            if title.lower() in bad_titles:
                continue
            if "END OF PATCH" in title.upper():
                continue
            if key_rx.search(title):
                out.append(title)
            continue

        ml = list_rx.match(t)
        if ml:
            body = _norm(ml.group(1).replace("**", ""))
            if not body:
                continue
            if "END OF PATCH" in body.upper():
                continue
            if key_rx.search(body):
                out.append(body)
            continue

        if "=>" in t:
            body2 = _norm(t.replace("**", ""))
            if key_rx.search(body2):
                out.append(body2)

    # de-dup preserve order
    seen = set()
    dedup: List[str] = []
    for x in out:
        k = x.lower()
        if k in seen:
            continue
        seen.add(k)
        dedup.append(x)

    return dedup[:MAX_TASKS_PER_PATCH]

def _render_tasks(p: Path, state_map: Dict[str, str]) -> List[str]:
    tag = p.stem.replace("TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_", "").replace("_PATCH", "")
    md = p.read_text(encoding="utf-8", errors="replace")
    reqs = _extract_reqs(md)

    lines: List[str] = []
    lines += [f"### {tag} 條款落地任務 / {tag} Compliance Tasks (AUTO)", ""]
    lines += [f"- 說明：保守抽取 `{p.name}` 的關鍵條款（上限 {MAX_TASKS_PER_PATCH} 條/檔）避免任務爆量；完成後勾選 [x]。", ""]

    for i, r in enumerate(reqs, 1):
        seed = tag + "|" + r
        tid = f"M8-{tag.upper()}-{i:03d}-{_sid(seed)}"
        title = r if " / " in r else f"{r} / {r}"
        mark = state_map.get(tid, " ")
        lines.append(f"- [{mark}] [TASK:{tid}] **{title}**")

    lines.append("")
    return lines

def _strip_legacy_blocks(board_text: str) -> str:
    """
    Remove any legacy marker blocks entirely.
    """
    # Remove all occurrences of legacy blocks (non-greedy)
    if LEG_BEGIN in board_text and LEG_END in board_text:
        board_text = re.sub(re.escape(LEG_BEGIN) + r".*?" + re.escape(LEG_END) + r"\s*", "", board_text, flags=re.S)
    return board_text

def _strip_duplicate_patch_tasks_after_end(board_text: str) -> str:
    """
    Your board currently shows duplicate patch tasks AFTER AUTO_PATCH_TASKS_END.
    Safest deterministic cleanup:
    - Find region between END and "## Always-On Bibles"
    - If that region contains M8 patch tasks or Patch-to-Tasks headings, wipe that region.
    """
    end_pos = board_text.find(END)
    if end_pos < 0:
        return board_text
    end_pos2 = end_pos + len(END)

    anchor = "## Always-On Bibles"
    a_pos = board_text.find(anchor, end_pos2)
    if a_pos < 0:
        return board_text

    mid = board_text[end_pos2:a_pos]
    # if duplicate patch artifacts appear here, remove them
    if ("Patch-to-Tasks" in mid) or ("條款落地任務" in mid) or ("[TASK:M8-" in mid) or ("v18.x 補強條款" in mid) or ("### vv18" in mid):
        board_text = board_text[:end_pos2] + "\n\n" + board_text[a_pos:]
    return board_text

def main() -> None:
    if not BOARD.exists():
        raise SystemExit(f"[FATAL] board not found: {BOARD}")

    board = BOARD.read_text(encoding="utf-8", errors="replace")
    board = _ensure_markers(board)
    board = _strip_legacy_blocks(board)

    state_map = _extract_task_state_map_in_auto_block(board)

    auto: List[str] = []
    auto += [BEGIN, "", "## v18.x 補強條款 → 任務清單（自動生成） / Patch-to-Tasks (AUTO)", ""]

    tasks_total = 0
    for p in PATCHES:
        if p.exists():
            part = _render_tasks(p, state_map)
            auto.extend(part)
            tasks_total += sum(1 for ln in part if "[TASK:" in ln)
        else:
            auto += [f"- [!] [TASK:M8-MISSING-{p.name}] **缺少 patch 檔案：{p.name} / Missing patch file: {p.name}**", ""]
            tasks_total += 1

    auto.append(END)

    board2 = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), "\n".join(auto), board, flags=re.S)
    board2 = _strip_duplicate_patch_tasks_after_end(board2)

    if board2 != board:
        BOARD.write_text(board2, encoding="utf-8")
        print(f"[OK] updated board patch tasks: {BOARD} preserved_states={len(state_map)} tasks={tasks_total}")
    else:
        print(f"[OK] no change: {BOARD} preserved_states={len(state_map)} tasks={tasks_total}")

if __name__ == "__main__":
    main()
