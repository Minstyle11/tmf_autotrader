#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/tmf_autotrader"

BOARD="docs/board/PROJECT_BOARD.md"
test -f "$BOARD" || { echo "[FATAL] missing: $BOARD"; exit 2; }

# 1) m6 status line must exist and be unique
m6_cnt="$(grep -cE '^\*\*專案總完成度[[:space:]]*/[[:space:]]*Overall completion:\*\*' "$BOARD" || true)"
if [[ "$m6_cnt" != "1" ]]; then
  echo "[FAIL] m6 status line count != 1 (got=$m6_cnt)"
  exit 3
fi

# 2) AUTO:PROGRESS markers must exist
grep -q '<!-- AUTO:PROGRESS_BEGIN -->' "$BOARD" || { echo "[FAIL] missing AUTO:PROGRESS_BEGIN"; exit 4; }
grep -q '<!-- AUTO:PROGRESS_END -->'   "$BOARD" || { echo "[FAIL] missing AUTO:PROGRESS_END"; exit 5; }

# 3) AUTO:PROGRESS must contain numeric fields (best-effort strict)
grep -qE '^- \*\*TOTAL_TASKS:\*\* [0-9]+' "$BOARD" || { echo "[FAIL] TOTAL_TASKS not numeric"; exit 6; }
grep -qE '^- \*\*DONE_TASKS:\*\* [0-9]+'  "$BOARD" || { echo "[FAIL] DONE_TASKS not numeric"; exit 7; }
grep -qE '^- \*\*PCT:\*\* [0-9]+(\.[0-9]+)?%' "$BOARD" || { echo "[FAIL] PCT not numeric%"; exit 8; }

# 4) m8 patch tasks block must exist (markers)
grep -q '<!-- AUTO:PATCH_TASKS_BEGIN -->' "$BOARD" || { echo "[FAIL] missing AUTO:PATCH_TASKS_BEGIN"; exit 9; }
grep -q '<!-- AUTO:PATCH_TASKS_END -->'   "$BOARD" || { echo "[FAIL] missing AUTO:PATCH_TASKS_END"; exit 10; }

# 5) sanity: header must still contain the quick header line "- 專案總完成度："
grep -qE '^- 專案總完成度：' "$BOARD" || { echo "[FAIL] missing header completion line"; exit 11; }

echo "[PASS] verify_pm_refresh_board_v1: m6/m8/progress/header all OK"
