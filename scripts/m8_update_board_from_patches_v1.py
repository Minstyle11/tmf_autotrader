from __future__ import annotations
from pathlib import Path
import re, hashlib

ROOT = Path.cwd()
BOARD = ROOT / "docs/board/PROJECT_BOARD.md"
PATCH_DIR = ROOT / "docs/bibles/patches"
PATCHES = [
    PATCH_DIR / "TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18_1_PATCH.md",
    PATCH_DIR / "TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18_2_PATCH.md",
]

BEGIN = "<!-- AUTO:PATCH_TASKS_BEGIN -->"
END   = "<!-- AUTO:PATCH_TASKS_END -->"

STRONG = re.compile(r"(?:\bMUST\b|\bSHALL\b|\bMUST NOT\b|必須|不得|嚴禁|強制|不可違反)", re.I)
HEAD   = re.compile(r"^(#{2,3})\s+(.+?)\s*$")

def sid(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:8]

def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

def extract(md: str) -> list[str]:
    out: list[str] = []
    for ln in md.splitlines():
        t = ln.strip()
        if not t or t.startswith("```") or t.startswith(">"):
            continue
        m = HEAD.match(t)
        if m:
            title = norm(m.group(2))
            if title and title.lower() not in ("patch", "overview", "scope", "changelog"):
                out.append(title)
            continue
        if STRONG.search(t):
            t = re.sub(r"^\s*[-*]\s+", "", t)
            t = norm(t)
            if len(t) > 160:
                t = t[:157] + "..."
            out.append(t)
    # de-dup preserve order
    seen = set()
    dedup: list[str] = []
    for x in out:
        k = x.lower()
        if k in seen: 
            continue
        seen.add(k)
        dedup.append(x)
    return dedup[:80]

def render(p: Path) -> list[str]:
    tag = p.stem.replace("TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_", "").replace("_PATCH", "")
    md = p.read_text(encoding="utf-8", errors="replace")
    reqs = extract(md)

    lines: list[str] = []
    lines += [f"### v{tag} 條款落地任務 / v{tag} Compliance Tasks (AUTO)", ""]
    lines += [f"- 說明：由程式自動擷取 `{p.name}` 的標題與強制詞條款；完成後勾選 [x]。如需調整映射，請走 OFFICIAL v18.x patch。", ""]
    for i, r in enumerate(reqs, 1):
        tid = f"M8-{tag.upper()}-{i:02d}-{sid(tag+'|'+r)}"
        title = r if " / " in r else f"{r} / {r}"
        lines.append(f"- [ ] [TASK:{tid}] **{title}**")
    lines.append("")
    return lines

def ensure_markers(s: str) -> str:
    if BEGIN in s and END in s:
        return s
    # Insert near first occurrence of v18.1/v18.2 section if exists; else append
    m = re.search(r"^##\s+v18\.1.*$", s, flags=re.M)
    if m:
        ins = m.end()
        return s[:ins] + "\n\n" + BEGIN + "\n" + END + "\n" + s[ins:]
    return s.rstrip() + "\n\n" + BEGIN + "\n" + END + "\n"

def main() -> None:
    if not BOARD.exists():
        raise SystemExit(f"[FATAL] board not found: {BOARD}")

    s = BOARD.read_text(encoding="utf-8")
    s = ensure_markers(s)

    auto: list[str] = []
    auto += [BEGIN, "", "## v18.1 / v18.2 補強條款 → 任務清單（自動生成） / Patch-to-Tasks (AUTO)", ""]
    for p in PATCHES:
        if p.exists():
            auto.extend(render(p))
        else:
            auto += [f"- [ ] [TASK:M8-MISSING-{p.name}] **缺少 patch 檔案：{p.name} / Missing patch file: {p.name}**", ""]
    auto.append(END)

    s2 = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), "\n".join(auto), s, flags=re.S)
    if s2 != s:
        BOARD.write_text(s2, encoding="utf-8")
        print("[OK] updated board patch tasks:", BOARD)
    else:
        print("[OK] no change:", BOARD)

if __name__ == "__main__":
    main()
