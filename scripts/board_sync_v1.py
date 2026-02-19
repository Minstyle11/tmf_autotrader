#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import argparse, re, textwrap

def die(msg:str, code:int=2):
    print(f"[FATAL] {msg}")
    raise SystemExit(code)

def _strip_code_fences(lines):
    out=[]
    in_code=False
    for ln in lines:
        if ln.strip().startswith("```"):
            in_code = not in_code
            out.append(ln); continue
        out.append(ln)
    return out

def compute_counts(md:str):
    lines = _strip_code_fences(md.splitlines())
    cb=[]
    for ln in lines:
        m = re.match(r'^\s*-\s*\[( |x|~|!)\]\s', ln)
        if m:
            cb.append(m.group(1))
    total=len(cb)
    done=sum(1 for s in cb if s=="x")
    doing=sum(1 for s in cb if s=="~")
    blocked=sum(1 for s in cb if s=="!")
    todo=sum(1 for s in cb if s==" ")
    pct=(done/total*100.0) if total else 0.0
    return dict(total=total, done=done, doing=doing, blocked=blocked, todo=todo, pct=pct)

def _sanitize_nonauto_progress_lines_v1(md: str) -> str:
    """
    Remove/neutralize any progress lines OUTSIDE AUTO blocks.
    Goal: enforce One-Truth (AUTO_PROGRESS + AUTO:PROGRESS).
    We keep content but strip %/numbers to avoid conflicting 'truth'.
    """
    # Temporarily protect AUTO blocks
    auto1_pat = r'<!-- AUTO_PROGRESS_START -->.*?<!-- AUTO_PROGRESS_END -->'
    auto2_pat = r'<!-- AUTO:PROGRESS_BEGIN -->.*?<!-- AUTO:PROGRESS_END -->'
    auto1 = re.search(auto1_pat, md, flags=re.S)
    auto2 = re.search(auto2_pat, md, flags=re.S)

    token1 = "<AUTO_PROGRESS_BLOCK>"
    token2 = "<AUTO_PROGRESS_KV_BLOCK>"

    md_work = md
    if auto1:
        md_work = re.sub(auto1_pat, token1, md_work, flags=re.S)
    if auto2:
        md_work = re.sub(auto2_pat, token2, md_work, flags=re.S)

    lines = md_work.splitlines(True)

    out = []
    in_code = False
    # lines that often create conflict: contains completion/progress + percent
    pat = re.compile(r'(專案總完成度|Overall\s+completion).*?\d+(\.\d+)?%')

    for ln in lines:
        if ln.strip().startswith("```"):
            in_code = not in_code
            out.append(ln)
            continue
        if (not in_code) and pat.search(ln):
            # Neutralize: keep a pointer WITHOUT numbers/percent
            out.append(re.sub(pat, r'進度（請以 AUTO_PROGRESS 區塊為準）', ln))
            # Also remove any remaining % number fragments on same line
            out[-1] = re.sub(r'\d+(\.\d+)?%|$begin:math:text$\\s\*已完成\\s\*\\d\+\\s\*\/\\s\*\\d\+\\s\*項\.\*\?$end:math:text$', '', out[-1])
            continue
        out.append(ln)

    md_work2 = "".join(out)

    # Restore AUTO blocks
    if auto1:
        md_work2 = md_work2.replace(token1, auto1.group(0))
    if auto2:
        md_work2 = md_work2.replace(token2, auto2.group(0))
    return md_work2

def replace_block(md:str, start:str, end:str, payload:str):
    sidx = md.find(start); eidx = md.find(end)
    if sidx<0 or eidx<0 or eidx<sidx:
        die(f"marker missing or invalid: {start} .. {end}")
    before = md[:sidx+len(start)]
    after  = md[eidx:]
    return before + "\n" + payload.rstrip("\n") + "\n" + after

def build_auto_progress_payload(c):
    return textwrap.dedent(f"""        **專案總完成度 / Overall completion:** {c['pct']:.1f}%（已完成 {c['done']} / {c['total']} 項；未完成 {c['total']-c['done']} 項）

    - done   : {c['done']}
    - doing  : {c['doing']}
    - blocked: {c['blocked']}
    - todo   : {c['todo']}
    - invalid_like: 0
    """).rstrip()

def build_auto_progress_kv_payload(c, last_update="(auto)"):
    return textwrap.dedent(f"""        - **TOTAL:** {c['total']}
    - **TOTAL_TASKS:** {c['total']}
    - **TODO:** {c['todo']}
    - **DOING:** {c['doing']}
    - **DONE:** {c['done']}
    - **DONE_TASKS:** {c['done']}
    - **BLOCKED:** {c['blocked']}
    - **PCT:** {c['pct']:.1f}%
    - **LAST_BOARD_UPDATE_AT:** {last_update}
    """).rstrip()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--board", default="docs/board/PROJECT_BOARD.md")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    p = Path(args.board)
    if not p.exists():
        die(f"missing board: {p}")

    md = p.read_text(encoding="utf-8", errors="replace")
    c = compute_counts(md)

    m = re.search(r'^\s*-\s*\*\*LAST_BOARD_UPDATE_AT:\*\*\s*(.+?)\s*$', md, flags=re.M)
    last_update = m.group(1).strip() if m else "(auto)"

    md2 = md
    md2 = replace_block(md2, "<!-- AUTO_PROGRESS_START -->", "<!-- AUTO_PROGRESS_END -->", build_auto_progress_payload(c))
    md2 = replace_block(md2, "<!-- AUTO:PROGRESS_BEGIN -->", "<!-- AUTO:PROGRESS_END -->", build_auto_progress_kv_payload(c, last_update))

    if args.write and (md2 != md):
        p.write_text(md2, encoding="utf-8")
        print(f"[OK] board synced: {p}")
    elif args.write:
        print(f"[OK] board already synced: {p}")

    if args.check:
        tmp = md2
        tmp = re.sub(r'<!-- AUTO_PROGRESS_START -->.*?<!-- AUTO_PROGRESS_END -->', '<AUTO_PROGRESS_BLOCK>', tmp, flags=re.S)
        tmp = re.sub(r'<!-- AUTO:PROGRESS_BEGIN -->.*?<!-- AUTO:PROGRESS_END -->', '<AUTO_PROGRESS_KV_BLOCK>', tmp, flags=re.S)
        # Any other 'completion' lines outside auto blocks are forbidden (One-Truth).
        if re.search(r'專案總完成度.*?\d+(\.\d+)?%|Overall completion.*?\d+(\.\d+)?%', tmp):
            die("found extra progress lines outside AUTO blocks; remove/stop writing manual progress elsewhere")
        c2 = compute_counts(md2)
        if c2["total"] <= 0:
            die("no task checkboxes found")
        if (c2["done"] + c2["todo"] + c2["doing"] + c2["blocked"]) != c2["total"]:
            die("status counts do not sum to total")
        print(f"[PASS] board check OK: TOTAL={c2['total']} DONE={c2['done']} TODO={c2['todo']} DOING={c2['doing']} BLOCKED={c2['blocked']} PCT={c2['pct']:.1f}%")

if __name__ == "__main__":
    main()
