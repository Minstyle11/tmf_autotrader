#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/tmf_autotrader"
echo "=== [m3 regression paper live smoke v1] start $(date -Iseconds) ==="

DB="runtime/data/tmf_db_smoke.sqlite3"
rm -f "$DB" || true

TMF_DEV_RECORDER_HARD_EXIT=1 TMF_DB_PATH="$DB" MAX_SECONDS=8 python3 src/broker/shioaji_recorder.py

# seed bidask into smoke DB to avoid SAFETY_BIDASK_MISSING when recorder window is too short/off-hours
python3 scripts/ops_seed_bidask_now_v1.py --db "$DB" --code TMFB6 --bid 31774 --ask 31775 --clear-cooldown=1 --source-file "m3_regression_paper_live_smoke_v1"


# strict in live: 15s budget for smoke; must pass immediately after recorder
TMF_DB_PATH="$DB" TMF_MAX_BIDASK_AGE_SECONDS=15 python3 src/oms/run_paper_live_v1.py --db "$DB"

echo "=== [m3 regression paper live smoke v1] PASS $(date -Iseconds) ==="
