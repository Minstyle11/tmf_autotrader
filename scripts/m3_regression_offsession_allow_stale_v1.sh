#!/usr/bin/env bash
set -euo pipefail

DB="${1:-${TMF_DB_PATH:-runtime/data/tmf_autotrader_v1.sqlite3}}"

echo "=== [m3 offsession allow-stale regression v1] DB=$DB ==="
# Force off-session window so SystemSafetyEngineV1 HARDGUARD will NOT disable allow-stale.
# Then set max-age=1s so stale is guaranteed, and request TMF_DEV_ALLOW_STALE_BIDASK=1.
OUT=$(
  TMF_MAX_BIDASK_AGE_SECONDS=1 \
  TMF_DEV_ALLOW_STALE_BIDASK=1 \
  TMF_SESSION_OPEN_HHMM=0000 \
  TMF_SESSION_CLOSE_HHMM=0001 \
  python3 src/oms/run_paper_live_v1.py --db "$DB" 2>&1 || true
)

echo "$OUT"

if echo "$OUT" | grep -q "OK_DEV_ALLOW_STALE"; then
  echo "[PASS] OK_DEV_ALLOW_STALE reachable off-session"
  exit 0
fi

echo "[FAIL] expected OK_DEV_ALLOW_STALE not found" >&2
exit 2
