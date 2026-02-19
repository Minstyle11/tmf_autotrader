#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse

BOARD = Path("docs/board/PROJECT_BOARD.md")

def _read_utf8(p: Path) -> str:
    b = p.read_bytes()
    try:
        return b.decode("utf-8")
    except UnicodeDecodeError as e:
        raise SystemExit(f"[FATAL] not utf-8: {e}")

def _atomic_write_utf8_lf(p: Path, s: str) -> None:
    # force LF + single final newline
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = s.rstrip("\n") + "\n"
    tmp = p.with_name(p.name + ".tmp_write")
    tmp.write_bytes(s.encode("utf-8"))
    tmp.replace(p)

def normalize(s: str):
    changed = False
    stats = {}

    # normalize CRLF/CR -> LF
    s0 = s
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    if s != s0:
        changed = True
        stats["crlf_to_lf"] = True

    # replace literal backslash-n sequences with actual newline
    cnt = s.count("\\n")
    if cnt:
        s = s.replace("\\n", "\n")
        changed = True
    stats["literal_backslash_n_fixed"] = cnt

    # remove lines that are only backslashes (\\ or \)
    lines = s.splitlines(True)
    drop = 0
    out = []
    for ln in lines:
        t = ln.strip()
        if t in ("\\", "\\\\"):
            drop += 1
            continue
        out.append(ln)
    if drop:
        s = "".join(out)
        changed = True
    stats["weird_only_lines_removed"] = drop

    # enforce single final newline
    s1 = s
    s = s.rstrip("\n") + "\n"
    if s != s1:
        changed = True
        stats["final_newline_fixed"] = True

    return s, changed, stats

def check_invariants(s: str):
    probs = []
    if "\\n" in s:
        probs.append("literal \\n exists")
    weird_only = [ln for ln in s.splitlines() if ln.strip() in ("\\", "\\\\")]
    if weird_only:
        probs.append(f"weird-only lines count={len(weird_only)}")
    if "\r" in s:
        probs.append("CR/CRLF exists")
    if not s.endswith("\n"):
        probs.append("missing final newline")
    if s.endswith("\n\n"):
        probs.append("multiple final newlines")
    return probs

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    if not BOARD.exists():
        raise SystemExit(f"[FATAL] missing: {BOARD}")

    s = _read_utf8(BOARD)
    s2, changed, stats = normalize(s)

    if args.fix:
        if changed:
            _atomic_write_utf8_lf(BOARD, s2)
            print(f"[OK] fixed: {BOARD} stats={stats}")
        else:
            print(f"[OK] nofix needed: {BOARD} stats={stats}")

    if args.check or (not args.fix):
        s_chk = _read_utf8(BOARD)
        probs = check_invariants(s_chk)
        if probs:
            print("[FAIL] PROJECT_BOARD invariants violated:")
            for x in probs:
                print(" -", x)
            raise SystemExit(2)
        print("[PASS] PROJECT_BOARD invariants OK")

if __name__ == "__main__":
    main()
