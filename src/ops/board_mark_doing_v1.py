from __future__ import annotations
from pathlib import Path
import re

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip()).lower()

def mark_doing_in_project_board(
    *,
    board_path: str = "docs/board/PROJECT_BOARD.md",
    milestones_header_regex: str = r"^##\s+Milestones\b",
    next_step_path_candidates = ("runtime/ops/NEXT_STEP.txt", "runtime/ops/NEXT_STEP.md"),
) -> bool:
    """
    Ensure PROJECT_BOARD has exactly ONE '[~] DOING' item.
    Priority:
      1) If NEXT_STEP file exists -> fuzzy match its first non-empty line to a TODO item.
      2) Else -> first TODO item within Milestones section.
    NOTE: GitHub tasklists officially support only [ ] and [x]; [~] is custom status.
    We still keep [~] per project legend and for deterministic automation.
    """
    bp = Path(board_path)
    if not bp.exists():
        return False

    lines = bp.read_text(encoding="utf-8", errors="replace").splitlines()

    # locate milestones section (start index)
    ms_start = None
    ms_end = len(lines)
    rx_ms = re.compile(milestones_header_regex)
    for i, ln in enumerate(lines):
        if rx_ms.search(ln):
            ms_start = i
            break
    if ms_start is None:
        ms_start = 0
    else:
        # end at next top-level header
        for j in range(ms_start + 1, len(lines)):
            if re.match(r"^#\s+", lines[j]):
                ms_end = j
                break

    # clear existing [~] anywhere except legend lines
    changed = False
    for i, ln in enumerate(lines):
        if "- [~]" in ln:
            # keep legend untouched
            if re.search(r"Status Legend", "\n".join(lines[max(0,i-3):i+3]), re.I):
                continue
            lines[i] = ln.replace("- [~]", "- [ ]", 1)
            changed = True

    # load next-step hint (optional)
    hint = ""
    for cand in next_step_path_candidates:
        p = Path(cand)
        if p.exists():
            txt = p.read_text(encoding="utf-8", errors="replace").splitlines()
            for ln in txt:
                if ln.strip():
                    hint = ln.strip()
                    break
        if hint:
            break
    hint_n = _norm(hint)

    # gather TODO candidates within milestones
    todo_idx = []
    for i in range(ms_start, ms_end):
        ln = lines[i]
        if re.match(r"^\s*-\s+\[\s\]\s+", ln):
            todo_idx.append(i)

    def _score(line: str) -> int:
        # simple token overlap score
        if not hint_n:
            return 0
        a = set(re.findall(r"[a-z0-9_]+", hint_n))
        b = set(re.findall(r"[a-z0-9_]+", _norm(line)))
        return len(a & b)

    pick = None
    if hint_n and todo_idx:
        scored = sorted((( _score(lines[i]), i) for i in todo_idx), reverse=True)
        if scored and scored[0][0] > 0:
            pick = scored[0][1]

    if pick is None:
        pick = todo_idx[0] if todo_idx else None

    if pick is not None:
        lines[pick] = lines[pick].replace("- [ ]", "- [~]", 1)
        changed = True

    if changed:
        bp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return changed
