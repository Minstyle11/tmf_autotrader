#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

LOGDIR="$ROOT/runtime/logs"
mkdir -p "$LOGDIR"
OUT="$LOGDIR/daily_report_v1.out.log"
ERR="$LOGDIR/daily_report_v1.err.log"
exec >>"$OUT" 2>>"$ERR"

echo "=== [daily_report_v1] start $(date "+%F %T") ==="

# Always refresh canonical PROJECT_BOARD + verify (constitutional dashboard gate)
if [[ -x scripts/pm_refresh_board_and_verify.sh ]]; then
  scripts/pm_refresh_board_and_verify.sh daily_report_v1
else
  echo "[FATAL] missing executable: scripts/pm_refresh_board_and_verify.sh" >&2
  exit 2
fi

# Optional: daily finance close pack (non-fatal if absent)
if [[ -x scripts/run_daily_finance_close_pack_daily_v1.sh ]]; then
  scripts/run_daily_finance_close_pack_daily_v1.sh daily_report_v1 || true
fi

echo "=== [daily_report_v1] done $(date "+%F %T") ==="
exit 0
