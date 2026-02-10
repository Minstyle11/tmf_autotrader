#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/tmf_autotrader"

python3 - <<'PY'
from pathlib import Path
import re
from datetime import datetime

p = Path("docs/board/PROJECT_BOARD.md")
s = p.read_text(encoding="utf-8", errors="replace")

now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Exclusion rules:
# - Exclude Status Legend block checkboxes and known legend/desc lines
EXACT_EXCLUDE = {
    "- [ ] 進行中、[!] 阻塞、[x] 已完成。",
    "- [ ] TODO",
    "- [~] DOING",
    "- [x] DONE",
    "- [!] BLOCKED",
}

def is_in_status_legend(lines, i):
    # Consider "Status Legend" section from its header until the next "## " header (excluding itself).
    # This avoids counting legend items as real tasks.
    # Find nearest preceding "## " header
    j = i
    while j >= 0 and not re.match(r'^\s*##\s+.+$', lines[j]):
        j -= 1
    if j < 0:
        return False
    hdr = lines[j].strip()
    if hdr != "## Status Legend":
        return False
    # If we are inside Status Legend, it remains until next "## " header after j
    # but since j is nearest preceding header, that means we're in the legend.
    return True

pat = re.compile(r'^\s*-\s*\[(?P<mark>[ xX~!])\]\s+(?P<body>.+?)\s*$')

todo = doing = done = blocked = 0
lines = s.splitlines()

for i, line in enumerate(lines):
    m = pat.match(line)
    if not m:
        continue

    stripped = line.strip()
    if stripped in EXACT_EXCLUDE:
        continue
    if is_in_status_legend(lines, i):
        continue

    mark = m.group("mark")
    if mark in ("x", "X"):
        done += 1
    elif mark == "~":
        doing += 1
    elif mark == "!":
        blocked += 1
    else:
        todo += 1

total = todo + doing + done + blocked
pct = (done / total * 100.0) if total else 0.0
open_ = total - done

legacy = f"**專案總完成度 / Overall completion:** {pct:.1f}%（已完成 {done} / {total} 項；未完成 {open_} 項）"
header_updated_at = f"- 更新時間：{now}"
header_completion = f"- 專案總完成度：{pct:.1f}% （已完成 {done} / {total} 項；TODO {todo} / DOING {doing} / BLOCKED {blocked}）"

def replace_or_insert_header(text: str) -> str:
    lines2 = text.splitlines(True)
    out = []
    saw_updated = False
    saw_completion = False

    for l in lines2:
        if re.match(r'^\s*-\s*更新時間：.*$', l):
            out.append(header_updated_at + "\n")
            saw_updated = True
            continue
        if re.match(r'^\s*-\s*專案總完成度：.*$', l):
            out.append(header_completion + "\n")
            saw_completion = True
            continue
        out.append(l)

    if not (saw_updated and saw_completion):
        out2 = []
        inserted = False
        for l in out:
            out2.append(l)
            if (not inserted) and re.match(r'^\s*#\s+.+$', l):
                out2.append("\n")
                if not saw_updated:
                    out2.append(header_updated_at + "\n")
                if not saw_completion:
                    out2.append(header_completion + "\n")
                out2.append("\n")
                inserted = True
        out = out2

    return "".join(out)

def update_auto_progress_block(text: str) -> str:
    begin = "<!-- AUTO:PROGRESS_BEGIN -->"
    end   = "<!-- AUTO:PROGRESS_END -->"
    if begin not in text or end not in text:
        return text

    block = "\n".join([
        begin,
        f"- **TOTAL:** {total}",
        f"- **TODO:** {todo}",
        f"- **DOING:** {doing}",
        f"- **DONE:** {done}",
        f"- **BLOCKED:** {blocked}",
        f"- **PCT:** {pct:.1f}%",
        f"- **LAST_BOARD_UPDATE_AT:** {now}",
        end
    ])

    pattern = re.escape(begin) + r".*?" + re.escape(end)
    return re.sub(pattern, block, text, flags=re.S)

def update_legacy_line_if_present(text: str) -> str:
    if re.search(r'^\*\*專案總完成度\s*/\s*Overall completion:\*\*.*$', text, flags=re.M):
        return re.sub(
            r'^\*\*專案總完成度\s*/\s*Overall completion:\*\*.*$',
            legacy,
            text,
            flags=re.M
        )
    return text

s2 = s
s2 = replace_or_insert_header(s2)
s2 = update_auto_progress_block(s2)
s2 = update_legacy_line_if_present(s2)

if s2 != s:
    p.write_text(s2, encoding="utf-8")

print(legacy)
PY
