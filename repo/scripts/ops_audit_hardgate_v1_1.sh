#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."

# v1_1 = v1 + Section 9 (paper-live integration smoke)
./scripts/ops_audit_hardgate_v1.sh

REPORT="runtime/handoff/state/audit_report_latest.md"
echo "" >> "$REPORT"
echo "## Section 9 — Paper-live integration smoke (RiskEngineV1 wired, reject reason persisted)" >> "$REPORT"
echo "- runner: src/oms/run_paper_live_v1.py" >> "$REPORT"
echo "- smoke : scripts/paper_live_integration_smoke_v1.sh" >> "$REPORT"
echo "" >> "$REPORT"

if ./scripts/paper_live_integration_smoke_v1.sh >> "$REPORT" 2>&1; then
  echo "[PASS] Section 9 paper-live integration smoke" >> "$REPORT"
else
  echo "[FATAL] Section 9 paper-live integration smoke FAILED" >> "$REPORT"
  exit 1
fi

echo "[OK] ops_audit_hardgate_v1_1 completed; report updated: $REPORT"
