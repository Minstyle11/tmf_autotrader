#!/usr/bin/env bash
# AUTO:CANONICAL_BOARD_PROGRESS_V1
python3 scripts/update_project_board_progress_v1.py >/dev/null 2>&1 || true
set -euo pipefail
cd "$(dirname "$0")/.."
python3 scripts/pm_refresh_board_v2.py

# --- CANONICAL_BOARD_PROGRESS_POST (must be last writer) ---
python3 scripts/update_project_board_progress_v1.py >/dev/null 2>&1 || true
# --- /CANONICAL_BOARD_PROGRESS_POST ---
