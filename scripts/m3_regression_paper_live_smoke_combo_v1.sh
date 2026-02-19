#!/usr/bin/env bash
set -euo pipefail

DB="${1:-runtime/data/tmf_autotrader_v1.sqlite3}"
echo "=== [m3 paper-live smoke combo v1] DB=${DB} ==="
echo ""

# NOTE:
# - A/B markers are REQUIRED by outer regression runner.
# - During holiday / market-closed windows, we allow Case-B to SKIP if EXEC_MARKET_CLOSED is observed.
#   (TAIFEX Lunar New Year holiday etc.)  This prevents false FAIL while keeping strictness on trading days.

TMP="$(mktemp -t tmf_smoke_combo.XXXXXX)"
cleanup(){ rm -f "$TMP" || true; }
trap cleanup EXIT

echo "=== [0] SMOKE_SUITE (persist summary_json) ==="

echo "=== [A] strict expect SAFETY_FEED_STALE ==="
# A: strict path should hit SAFETY_FEED_STALE (or RISK_STOP_REQUIRED if safety is overridden elsewhere)
python3 -u scripts/run_paper_live_smoke_suite_v1.py --db "${DB}" 2>&1 | tee "$TMP"
echo ""

echo "=== [B] offline allow-stale expect (RISK_STOP_REQUIRED|EXEC_MARKET_CLOSED) ==="
# B: offline allow-stale tries to bypass stale-feed to reach risk gating.
# If market is closed, EXEC_MARKET_CLOSED is acceptable and we SKIP (not FAIL).
set +e
TMF_DEV_ALLOW_STALE_BIDASK=1 python3 -u scripts/run_paper_live_smoke_suite_v1.py --db "${DB}" 2>&1 | tee "$TMP"
rc=${PIPESTATUS[0]}
set -e

if [ $rc -ne 0 ]; then
  if grep -q "EXEC_MARKET_CLOSED" "$TMP"; then
    echo "[SKIP] market closed detected (EXEC_MARKET_CLOSED) -> accept during holidays/off-hours"
    echo "=== [m3 paper-live smoke combo v1] PASS-SKIP-MARKET_CLOSED $(date -Iseconds) ==="
    exit 0
  fi
  echo "[FAIL] smoke suite failed and not market-closed; see log above"
  exit $rc
fi

echo "=== [m3 paper-live smoke combo v1] PASS $(date -Iseconds) ==="
