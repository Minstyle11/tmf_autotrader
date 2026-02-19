#!/usr/bin/env bash
set -euo pipefail

cd "$HOME/tmf_autotrader"

# 1) Recompute canonical checkbox-only block (AUTO_PROGRESS_START/END)
python3 scripts/update_project_board_progress_v2.py >/dev/null 2>&1 || true

# 2) Sync header + AUTO:PROGRESS_BEGIN/END to canonical block counts
python3 scripts/board_sync_header_to_canonical_v1.py >/dev/null 2>&1 || true

# 3) Emit ONE stable canonical line for LaunchAgent logs
python3 scripts/board_progress_from_block_v1.py | tail -n 1
