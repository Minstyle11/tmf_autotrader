#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/tmf_autotrader"

TS="$(date +%Y%m%d_%H%M%S)"
LOG="runtime/logs/m2_regression_suite_v1.run.${TS}.log"
LAST="runtime/logs/m2_regression_suite_v1.last.log"

{
  echo "=== [m2 regression suite v1] start $(date -Iseconds) ==="
  echo "=== [1/3] risk gates ==="
  bash scripts/m2_regression_risk_gates_v1.sh
  echo
  echo "=== [2/3] market-quality gates ==="
  bash scripts/m2_regression_market_quality_gates_v1.sh
  echo
  echo "=== [3/3] paper-live integration smoke ==="
  bash scripts/paper_live_integration_smoke_v1.sh
  echo
  echo "=== [m2 regression suite v1] PASS $(date -Iseconds) ==="
} 2>&1 | tee "$LOG"

cp -f "$LOG" "$LAST"
echo "[OK] wrote log: $LAST"
