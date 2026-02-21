#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/tmf_autotrader"
echo "=== [m3 regression paper live smoke v1] start $(date -Iseconds) ==="

DB="runtime/data/tmf_db_smoke.sqlite3"

# Build a consistent snapshot DB for smoke (avoid empty DB / missing tables)
python3 - <<'PYSNAP'
import os, sqlite3
src = "runtime/data/tmf_autotrader_v1.sqlite3"
dst = "runtime/data/tmf_db_smoke.sqlite3"
if os.path.exists(dst):
    os.remove(dst)
with sqlite3.connect(src) as con_src, sqlite3.connect(dst) as con_dst:
    con_src.backup(con_dst)
print("[OK] smoke DB snapshot created via sqlite backup:", dst)
PYSNAP

TMF_DEV_RECORDER_HARD_EXIT=1 TMF_DB_PATH="$DB" MAX_SECONDS=8 python3 src/broker/shioaji_recorder.py

# seed bidask into smoke DB to avoid SAFETY_BIDASK_MISSING when recorder window is too short/off-hours
python3 scripts/ops_seed_bidask_now_v1.py --db "$DB" --code TMFB6 --bid 31774 --ask 31775 --clear-cooldown=1 --source-file "m3_regression_paper_live_smoke_v1"

# strict in live: 15s budget for smoke; must pass immediately after recorder
TMP="$(mktemp -t tmf_paper_live_smoke.XXXXXX)"
set +e
TMF_DB_PATH="$DB" TMF_MAX_BIDASK_AGE_SECONDS=15 python3 src/oms/run_paper_live_v1.py --db "$DB" >"$TMP" 2>&1
RC="$?"
set -e

# If market is closed (holiday/offsession), treat as SKIP/PASS (regression-only)
if grep -q "EXEC_MARKET_CLOSED" "$TMP"; then
  echo "[SKIP] EXEC_MARKET_CLOSED detected (holiday/offsession) -> treat paper-live smoke as PASS"
  rm -f "$TMP"
  echo "=== [m3 regression paper live smoke v1] PASS $(date -Iseconds) ==="
  exit 0
fi

# Otherwise, enforce strict pass
cat "$TMP"
rm -f "$TMP"
if [ "$RC" -ne 0 ]; then
  echo "[FATAL] paper-live smoke failed rc=$RC" >&2
  exit "$RC"
fi

echo "=== [m3 regression paper live smoke v1] PASS $(date -Iseconds) ==="
