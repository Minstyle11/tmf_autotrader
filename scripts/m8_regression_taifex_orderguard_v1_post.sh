#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/tmf_autotrader"

./scripts/m8_regression_taifex_orderguard_v1.sh

python3 scripts/ops_mark_board_tasks_done_v1.py \
  M8-V18_1-08-ee50c910 \
  M8-V18_1-09-7fd37f6a \
  M8-V18_1-10-04ed66fc

python3 scripts/update_project_board_progress_v2.py
python3 scripts/board_sync_header_to_canonical_v1.py
python3 scripts/update_project_board_progress_v2.py

echo "[程序完成]"
