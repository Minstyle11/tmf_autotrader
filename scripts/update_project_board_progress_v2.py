#!/usr/bin/env python3
import datetime
from pathlib import Path

BOARD = Path("docs/board/PROJECT_BOARD.md")
STATE_DIR = Path("runtime/handoff/state")

LEGEND_SET = {"- [ ] TODO", "- [~] DOING", "- [x] DONE", "- [!] BLOCKED",
              "* [ ] TODO", "* [~] DOING", "* [x] DONE", "* [!] BLOCKED"}

def now_ts():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def now_human():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def _strip_leading_ws_and_bom(line: str) -> str:
    # tolerate BOM + arbitrary indent
    return line.lstrip("\ufeff").lstrip()

def is_task_strict(line: str):
    t = _strip_leading_ws_and_bom(line)
    # allow '-' or '*'
    if not (t.startswith("- [") or t.startswith("* [")):
        return False, None
    # strict: "<bullet> [<status>] " with status in " x~!"
    if len(t) < 7:
        return False, None
    status = t[4]
    if t[5] != "]":
        return False, None
    if status not in (" ", "x", "~", "!"):
        return False, None
    if not t[6].isspace():
        return False, None
    return True, status

def is_task_loose(line: str):
    t = _strip_leading_ws_and_bom(line).strip()
    if not (t.startswith("-") or t.startswith("*")):
        return False, None
    # normalize "-[x]" -> "- [x]" ; "*[x]" -> "* [x]"
    t2 = t.replace("-[", "- [").replace("*[", "* [")
    if not (t2.startswith("- [") or t2.startswith("* [")):
        return False, None
    try:
        close = t2.index("]")
    except ValueError:
        return False, None
    if close < 4:
        return False, None
    status = t2[4]
    if status not in (" ", "x", "~", "!"):
        return False, None
    return True, status

def compute(lines, mode="strict"):
    total = done = doing = blocked = 0
    items = []
    for i, l in enumerate(lines, start=1):
        s = l.rstrip("\n")
        if _strip_leading_ws_and_bom(s).strip() in LEGEND_SET:
            continue
        if mode == "strict":
            ok, st = is_task_strict(l)
        else:
            ok, st = is_task_loose(l)
        if not ok:
            continue
        total += 1
        if st == "x":
            done += 1
            status = "DONE"
        elif st == "~":
            doing += 1
            status = "DOING"
        elif st == "!":
            blocked += 1
            status = "BLOCKED"
        else:
            status = "TODO"
        items.append((i, status, s))
    pct = (done / total * 100.0) if total else 0.0
    return {"total": total, "done": done, "doing": doing, "blocked": blocked, "pct": pct, "items": items}

def replace_first_line(text: str, prefix: str, new_line: str):
    idx = text.find(prefix)
    if idx == -1:
        return text
    line_end = text.find("\n", idx)
    if line_end == -1:
        return text[:idx] + new_line + "\n"
    return text[:idx] + new_line + text[line_end:]

def upsert_auto_block(text: str, block: str):
    begin = text.find("<!-- AUTO:PROGRESS_BEGIN -->")
    endm  = text.find("<!-- AUTO:PROGRESS_END -->")
    if begin != -1 and endm != -1 and endm > begin:
        endm2 = endm + len("<!-- AUTO:PROGRESS_END -->")
        return text[:begin] + block + text[endm2:]
    parts = text.splitlines(True)
    ins = 0
    for i, l in enumerate(parts[:50]):
        if l.lstrip().startswith("# "):
            ins = i + 1
            break
    parts.insert(ins, block + "\n")
    return "".join(parts)

def write_audit(path: Path, title: str, stats: dict):
    out = []
    out.append(f"# {title}\n")
    out.append(f"- generated: {now_human()}\n")
    out.append(f"- total={stats['total']} done={stats['done']} doing={stats['doing']} blocked={stats['blocked']} pct={stats['pct']:.1f}%\n\n")
    by = {"DONE": [], "DOING": [], "BLOCKED": [], "TODO": []}
    for ln, st, raw in stats["items"]:
        by[st].append((ln, raw))
    for k in ["DONE", "DOING", "BLOCKED", "TODO"]:
        out.append(f"## {k} ({len(by[k])})\n")
        for ln, raw in by[k]:
            out.append(f"- L{ln}: {raw}\n")
        out.append("\n")
    path.write_text("".join(out), encoding="utf-8")

def main():
    if not BOARD.exists():
        raise SystemExit(f"missing: {BOARD}")
    s = BOARD.read_text(encoding="utf-8")
    lines = s.splitlines(True)

    ts = now_ts()
    bk = BOARD.with_name(BOARD.name + f".bak_autofix_{ts}")
    bk.write_text(s, encoding="utf-8")

    strict = compute(lines, mode="strict")
    loose  = compute(lines, mode="loose")

    auto_block = (
        "<!-- AUTO:PROGRESS_BEGIN -->\n"
        f"- **TOTAL_TASKS:** {strict['total']}\n"
        f"- **DONE_TASKS:** {strict['done']}\n"
        f"- **DOING_TASKS:** {strict['doing']}\n"
        f"- **BLOCKED_TASKS:** {strict['blocked']}\n"
        f"- **PCT:** {strict['pct']:.1f}%\n"
        "<!-- AUTO:PROGRESS_END -->"
    )
    s2 = upsert_auto_block(s, auto_block)

    s2 = replace_first_line(s2, "專案總完成度：", f"專案總完成度：{strict['pct']:.1f}% （已完成 {strict['done']} / {strict['total']} 項）")
    s2 = replace_first_line(s2, "- 更新時間：", f"- 更新時間：{now_human()}")

    marker = "**專案總完成度 / Overall completion:**"
    if marker in s2:
        s2 = replace_first_line(
            s2,
            marker,
            f"{marker} {strict['pct']:.1f}%（已完成 {strict['done']} / {strict['total']} 項；未完成 {strict['total']-strict['done']} 項；DOING {strict['doing']}；BLOCKED {strict['blocked']}）"
        )

    BOARD.write_text(s2, encoding="utf-8")

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    audit_strict = STATE_DIR / f"PROJECT_BOARD_TASK_AUDIT_STRICT_{ts}.md"
    audit_loose  = STATE_DIR / f"PROJECT_BOARD_TASK_AUDIT_LOOSE_{ts}.md"
    write_audit(audit_strict, "PROJECT_BOARD TASK AUDIT (STRICT)", strict)
    write_audit(audit_loose,  "PROJECT_BOARD TASK AUDIT (LOOSE)",  loose)

    strict_set = {(ln, raw) for (ln, st, raw) in strict["items"]}
    missed = [(ln, st, raw) for (ln, st, raw) in loose["items"] if (ln, raw) not in strict_set]
    diff_path = STATE_DIR / f"PROJECT_BOARD_TASK_AUDIT_DIFF_{ts}.md"
    diff_out = []
    diff_out.append("# PROJECT_BOARD TASK AUDIT DIFF (LOOSE - STRICT)\n")
    diff_out.append(f"- generated: {now_human()}\n")
    diff_out.append(f"- STRICT total={strict['total']} done={strict['done']} pct={strict['pct']:.1f}%\n")
    diff_out.append(f"- LOOSE  total={loose['total']} done={loose['done']} pct={loose['pct']:.1f}%\n")
    diff_out.append(f"- missed_by_strict={len(missed)}\n\n")
    diff_out.append("## missed_by_strict items\n")
    for ln, st, raw in missed:
        diff_out.append(f"- L{ln} [{st}] {raw}\n")
    diff_path.write_text("".join(diff_out), encoding="utf-8")

    print(f"[OK] PROJECT_BOARD recomputed (STRICT): total={strict['total']} done={strict['done']} doing={strict['doing']} blocked={strict['blocked']} pct={strict['pct']:.1f}%")
    print(f"[OK] PROJECT_BOARD recomputed (LOOSE) : total={loose['total']} done={loose['done']} doing={loose['doing']} blocked={loose['blocked']} pct={loose['pct']:.1f}%")
    print(f"[OK] backup: {bk}")
    print(f"[OK] audit(strict): {audit_strict}")
    print(f"[OK] audit(loose) : {audit_loose}")
    print(f"[OK] diff audit  : {diff_path}")

if __name__ == "__main__":
    main()
