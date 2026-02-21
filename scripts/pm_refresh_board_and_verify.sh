#!/usr/bin/env bash

# [ULTRA][CONSTITUTION] Fail-fast PROJECT_BOARD HardGate (must PASS)
python3 scripts/board_ultra_hardgate_v1.py
RC=$?
if [ "$RC" -ne 0 ]; then echo "[FATAL] PROJECT_BOARD hardgate failed rc=$RC" >&2; exit $RC; fi

set -euo pipefail
bash scripts/pm_refresh_board_canonical.sh
bash scripts/verify_pm_refresh_board_v1.sh
