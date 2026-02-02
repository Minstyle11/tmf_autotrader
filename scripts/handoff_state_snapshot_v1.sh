#!/usr/bin/env bash
set -euo pipefail
PROJ="$HOME/tmf_autotrader"
OUT="$PROJ/runtime/handoff/state/latest_state.json"
mkdir -p "$(dirname "$OUT")"

python3 - <<'PY'
import json, os, re, subprocess
from pathlib import Path
from datetime import datetime

proj = Path.home() / "tmf_autotrader"
board = proj / "docs/board/PROJECT_BOARD.md"
changelog = proj / "docs/board/CHANGELOG.md"

board_txt = board.read_text(encoding="utf-8") if board.exists() else ""
m = re.search(r"專案總完成度：([0-9.]+)%", board_txt)
board_pct = m.group(1) if m else ""

def launch_label_status(label: str) -> str:
    try:
        out = subprocess.check_output(["launchctl","list"], text=True, stderr=subprocess.DEVNULL)
        for line in out.splitlines():
            parts = line.split()
            if len(parts) >= 3 and parts[2] == label:
                return parts[1]  # status column
    except Exception:
        pass
    return ""

last_ch = ""
if changelog.exists():
    try:
        last_ch = changelog.read_text(encoding="utf-8").splitlines()[-1]
    except Exception:
        last_ch = ""

d = {
  "ts": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
  "board_total_pct": board_pct,
  "launchd": {
    "pm_tick": launch_label_status("com.tmf_autotrader.pm_tick"),
    "autorestart": launch_label_status("com.tmf_autotrader.autorestart"),
    "backup": launch_label_status("com.tmf_autotrader.backup"),
    "handoff_tick": launch_label_status("com.tmf_autotrader.handoff_tick"),
  },
  "last_changelog_line": last_ch,
  "paths": {
    "repo": str(proj),
    "handoff_log": "docs/handoff/HANDOFF_LOG.md",
    "opening_prompt_draft": "docs/handoff/NEW_WINDOW_OPENING_PROMPT_DRAFT.md",
    "next_step": "runtime/handoff/state/next_step.txt"
  }
}
outp = proj / "runtime/handoff/state/latest_state.json"
outp.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print("[state_snapshot] wrote", outp)
PY
