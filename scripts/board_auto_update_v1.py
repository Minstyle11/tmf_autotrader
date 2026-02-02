#!/usr/bin/env python3
# NOTE: Python 3.9.6 compatible
from __future__ import annotations
import re
import sys
from pathlib import Path
from datetime import datetime

def _ts_compact() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def _ts_human() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def backup(p: Path) -> Path:
    ts = _ts_compact()
    bak = p.with_name(p.name + f".bak_{ts}")
    bak.write_bytes(p.read_bytes())
    return bak

def append_changelog(changelog: Path, note: str) -> None:
    if not changelog.exists():
        raise FileNotFoundError(str(changelog))
    backup(changelog)
    line = f"- [{_ts_human()}] {note}\n"
    with changelog.open("a", encoding="utf-8") as f:
        f.write(line)

def update_project_board(board: Path) -> None:
    if not board.exists():
        raise FileNotFoundError(str(board))
    backup(board)
    s = board.read_text(encoding="utf-8", errors="replace").splitlines(True)

    # Replace the first occurrence of: "- 更新時間：...."
    pat = re.compile(r"^-\s*更新時間：.*$")
    replaced = False
    out_lines = []
    for line in s:
        if (not replaced) and pat.match(line.strip("\n")):
            out_lines.append(f"- 更新時間：{_ts_human()}\n")
            replaced = True
        else:
            out_lines.append(line)

    if not replaced:
        raise RuntimeError("cannot find '更新時間：' line to update in PROJECT_BOARD.md")

    board.write_text("".join(out_lines), encoding="utf-8")

def main(argv: list[str]) -> int:
    note = "pm_tick"
    if "--note" in argv:
        i = argv.index("--note")
        if i + 1 >= len(argv):
            print("[FATAL] --note requires a value", file=sys.stderr)
            return 2
        note = str(argv[i + 1])

    repo = Path(__file__).resolve().parents[1]
    changelog = repo / "docs" / "board" / "CHANGELOG.md"
    board = repo / "docs" / "board" / "PROJECT_BOARD.md"

    append_changelog(changelog, note)
    update_project_board(board)

    print(f"[OK] appended: {changelog} (+note={note})")
    print(f"[OK] updated : {board} (update_time={_ts_human()})")
    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
