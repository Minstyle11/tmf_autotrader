#!/usr/bin/env bash
set -euo pipefail
bash scripts/pm_refresh_board_canonical.sh
bash scripts/verify_pm_refresh_board_v1.sh
