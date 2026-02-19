from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import re

REPO = Path(".").resolve()

def _read(p: Path, limit: int | None = None) -> str:
    if not p.exists():
        return ""
    txt = p.read_text(encoding="utf-8", errors="replace")
    return txt if limit is None else txt[:limit]

def _tail(p: Path, n_lines: int = 80) -> str:
    if not p.exists():
        return ""
    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-n_lines:])

def _sha256_file(p: Path) -> str:

    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def _extract_board_digest_v1(board_path: Path) -> str:
    """
    Return ONLY the One-Truth digest blocks from PROJECT_BOARD to avoid stale noise.
    - AUTO_PROGRESS block
    - AUTO:PROGRESS kv block
    - Milestone completion lines (e.g. "- M0 ...", "- M1 ...")
    """
    if not board_path or (not board_path.exists()):
        return "(missing PROJECT_BOARD)"
    txt = board_path.read_text(encoding="utf-8", errors="replace")
    def grab_block(a: str, b: str) -> str:
        m = re.search(re.escape(a) + r"(.*?)" + re.escape(b), txt, flags=re.S)
        return (a + (m.group(1) if m else "") + b).strip()
    auto1 = grab_block("<!-- AUTO_PROGRESS_START -->", "<!-- AUTO_PROGRESS_END -->")
    auto2 = grab_block("<!-- AUTO:PROGRESS_BEGIN -->", "<!-- AUTO:PROGRESS_END -->")
    # Milestone completion lines
    ms = []
    for ln in txt.splitlines():
        if re.match(r'^\s*-\s*M\d+\s', ln):
            ms.append(ln.strip())
    out = []
    out.append(auto1)
    out.append("")
    out.append(auto2)
    if ms:
        out.append("")
        out.append("## 里程碑完成度（摘錄）")
        out.extend(ms[:30])
    return "\n".join(out).strip()


def _find_board() -> Path | None:
    # Prefer canonical, but allow repo drift.
    candidates = [
                REPO / "docs/board/PROJECT_BOARD.md",
            ]
    for c in candidates:
        if c.exists():
            return c
    found = [REPO / "docs/board/PROJECT_BOARD.md"]  # OFFICIAL canonical only

    # NOTE: do NOT glob **/PROJECT_BOARD.md; backups can shadow canonical.
    if found:
        return found[0]
    # fallback: any *board*.md
    found2 = list(REPO.glob("**/*BOARD*.md"))
    return found2[0] if found2 else None

def _latest_windowpack_zip() -> Path | None:
    d = REPO / "runtime/handoff/latest"
    if not d.exists():
        return None
    zips = sorted(d.glob("TMF_AutoTrader_WindowPack_ULTRA_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    return zips[0] if zips else None

def main():
    now = datetime.now(timezone.utc).astimezone()
    ts = now.isoformat(timespec="seconds")

    # One-Truth v18
    v18 = REPO / "docs/bibles/TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18.md"
    v18_ok = v18.exists()
    v18_sha = _sha256_file(v18) if v18_ok else ""

    # Board
    board = _find_board()
    board_excerpt = _read(board, limit=2600) if board else "(missing PROJECT_BOARD)"

    # Latest pack
    z = _latest_windowpack_zip()
    z_rel = str(z.relative_to(REPO)) if z else "(missing latest windowpack zip)"
    z_sha_sidecar = ""
    if z and (z.with_suffix(z.suffix + ".sha256.txt")).exists():
        z_sha_sidecar = _read(z.with_suffix(z.suffix + ".sha256.txt")).strip()

    # State docs
    audit_latest = REPO / "runtime/handoff/state/audit_report_latest.md"
    next_step = REPO / "runtime/handoff/state/next_step.txt"
    changelog = REPO / "CHANGELOG.md"
    handoff_log = REPO / "docs/handoff/HANDOFF_LOG.md"
    latest_state = REPO / "runtime/handoff/state/latest_state.json"

    out = REPO / "runtime/handoff/state/NEW_WINDOW_OPENING_PROMPT_ULTRA_ZH.md"
    out.parent.mkdir(parents=True, exist_ok=True)

    hard_gate_cmds = f"""```bash
cd ~/tmf_autotrader

# 1) v18 sha256 verify (ONE-TRUTH)
sha256sum docs/bibles/TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18.md | tee /tmp/v18.sha256
cat docs/bibles/TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18.md.sha256.txt

# 2) latest ULTRA windowpack sha256 verify (if you are using zip handoff)
sha256sum {z_rel} | tee /tmp/latest_pack.sha256
cat {z_rel}.sha256.txt

# 3) Read audit + next_step (then execute next_step as a bash script if it is executable-style)
sed -n '1,200p' runtime/handoff/state/audit_report_latest.md
sed -n '1,200p' runtime/handoff/state/next_step.txt
```"""

    md = []
    md.append("# TMF AutoTrader — NEW WINDOW OPENING PROMPT (ULTRA / OFFICIAL-LOCKED / v18 One-Truth)")
    md.append(f"- 生成時間：{ts}")
    md.append("")
    md.append("## 0) One-Truth / One-Doc / One-OS（絕對規則）")
    md.append("- 唯一真相源：`docs/bibles/TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18.md`（只允許 v18.x patch）。")
    md.append("- 任何與 v18 衝突者，一律以 v18 為準。")
    md.append("- 事件真相源：只認 DB 落盤 events（呼叫成功不算成立）。")
    md.append("")
    md.append("### v18 sha256（驗收必做）")
    md.append("```")
    md.append(f"{v18_sha}  TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18.md" if v18_ok else "(missing v18)")
    md.append("```")
    md.append(f"- v18 檔案存在：{v18_ok}")
    md.append("")
    md.append("## 1) 新視窗第一輪必做（Hard Gate / 不可跳）")
    md.append(hard_gate_cmds)
    md.append("")
    md.append("## 2) 最新 ULTRA WindowPack（接手用）")
    md.append(f"- latest_zip: `{z_rel}`")
    if z_sha_sidecar:
        md.append("```")
        md.append(z_sha_sidecar)
        md.append("```")
    else:
        md.append("- (missing zip sha256 sidecar)")
    md.append("")
    md.append("## 3) PROJECT_BOARD（摘錄）")
    md.append("```")
    md.append(board_excerpt.strip() if board_excerpt else "(empty)")
    md.append("```")
    md.append("")
    md.append("## 4) latest_state.json（原文）")
    md.append("```json")
    md.append(_read(latest_state, limit=2400).strip() or "{}")
    md.append("```")
    md.append("")
    md.append("## 5) audit_report_latest.md（尾段）")
    md.append("```")
    md.append(_tail(audit_latest, n_lines=80).strip() or "(missing audit_report_latest.md)")
    md.append("```")
    md.append("")
    md.append("## 6) next_step.txt（原文）")
    md.append("```")
    md.append(_read(next_step, limit=1600).strip() or "(missing next_step.txt)")
    md.append("```")
    md.append("")
    md.append("## 7) CHANGELOG（尾段）")
    md.append("```")
    md.append(_tail(changelog, n_lines=60).strip() or "(missing CHANGELOG.md)")
    md.append("```")
    md.append("")
    md.append("## 8) HANDOFF_LOG（尾段）")
    md.append("```")
    md.append(_tail(handoff_log, n_lines=80).strip() or "(missing docs/handoff/HANDOFF_LOG.md)")
    md.append("```")
    md.append("")
    md.append("## 9) 互動協議（強制）")
    md.append("- 每回合只跑一個 Terminal 指令；貼回輸出後才進下一步。")
    md.append("- 任何卡住（bquote>/cmdand/等待無輸出）不要叫使用者 Ctrl+C；直接給下一個新指令。")
    md.append("- 一切以 v18 為準（One-Truth）。")
    md.append("")

    new_text = "\n".join(md) + "\n"
    old_text = out.read_text(encoding="utf-8", errors="replace") if out.exists() else None
    changed = (old_text != new_text)

    if changed:
        import os, tempfile
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=str(out.parent), delete=False) as f:
            f.write(new_text)
            tmp_path = Path(f.name)
        os.replace(tmp_path, out)
        print("[OK] wrote:", str(out))
    else:
        print("[OK] unchanged:", str(out))

    sha = _sha256_file(out)
    sidecar = out.parent / (out.name + ".sha256.txt")
    desired = f"{sha}  {out.name}\n"
    cur = sidecar.read_text(encoding="utf-8", errors="replace") if sidecar.exists() else ""
    if cur != desired:
        sidecar.write_text(desired, encoding="utf-8")
        print("[OK] wrote:", str(sidecar))
    else:
        print("[OK] sidecar unchanged:", str(sidecar))

if __name__ == "__main__":
    main()
