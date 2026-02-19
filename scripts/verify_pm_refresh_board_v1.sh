#!/usr/bin/env bash
set -euo pipefail

BOARD="${BOARD:-docs/board/PROJECT_BOARD.md}"

bash scripts/pm_refresh_board_canonical.sh >/dev/null 2>&1 || true

[ -f "$BOARD" ] || { echo "[FAIL] missing board: $BOARD"; exit 2; }

m6_cnt="$(python3 - "$BOARD" <<'PY'
import sys, re
from pathlib import Path

board = Path(sys.argv[1])
txt = board.read_text(encoding="utf-8", errors="replace").splitlines()

AUTO_S="<!-- AUTO_PROGRESS_START -->"
AUTO_E="<!-- AUTO_PROGRESS_END -->"
pat = re.compile(r"^\*\*專案總完成度\s*/\s*Overall completion:\*\*")

in_auto=False
cnt=0
for ln in txt:
    if AUTO_S in ln:
        in_auto=True
        continue
    if AUTO_E in ln:
        in_auto=False
        continue
    if in_auto:
        continue
    if pat.match(ln.strip()):
        cnt += 1
print(cnt)
PY
)"
if [ "${m6_cnt}" != "1" ]; then
  echo "[FAIL] m6 status line count != 1 (got=${m6_cnt})"
  exit 3
fi

grep -q "<!-- AUTO:PROGRESS_BEGIN -->" "$BOARD" || { echo "[FAIL] missing AUTO:PROGRESS_BEGIN"; exit 4; }
grep -q "<!-- AUTO:PROGRESS_END -->"   "$BOARD" || { echo "[FAIL] missing AUTO:PROGRESS_END"; exit 5; }
grep -qE "^- \*\*TOTAL_TASKS:\*\* [0-9]+" "$BOARD" || { echo "[FAIL] TOTAL_TASKS not numeric"; exit 6; }
grep -qE "^- \*\*DONE_TASKS:\*\* [0-9]+"  "$BOARD" || { echo "[FAIL] DONE_TASKS not numeric"; exit 7; }
grep -qE "^- \*\*PCT:\*\* [0-9]+(\.[0-9]+)?%" "$BOARD" || { echo "[FAIL] PCT not numeric%"; exit 8; }

grep -q "<!-- AUTO:PATCH_TASKS_BEGIN -->" "$BOARD" || { echo "[FAIL] missing AUTO:PATCH_TASKS_BEGIN"; exit 9; }
grep -q "<!-- AUTO:PATCH_TASKS_END -->"   "$BOARD" || { echo "[FAIL] missing AUTO:PATCH_TASKS_END"; exit 10; }

grep -qE "^- 專案總完成度：" "$BOARD" || { echo "[FAIL] missing header completion line"; exit 11; }

echo "[PASS] verify_pm_refresh_board_v1: m6/m8/progress/header all OK"
