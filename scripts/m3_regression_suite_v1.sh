#!/usr/bin/env bash
set -euo pipefail

DB="${1:-${TMF_DB_PATH:-runtime/data/tmf_autotrader_v1.sqlite3}}"

say() { echo; echo "=== [$1] $(date -Iseconds) ==="; }

say "M3 REGRESSION SUITE v1 START"
echo "[INFO] DB=$DB"

# 1) Core policy/spec guards (must be solid before any trading smoke)
say "reject policy"
bash scripts/m3_regression_reject_policy_v1.sh

say "spec-diff stopper"
bash scripts/m3_regression_spec_diff_stopper_v1.sh "$DB"

# 2) Paper-live chain (STRICT + OFFLINE combo)
say "paper-live smoke combo"
bash scripts/m3_regression_paper_live_smoke_combo_v1.sh "$DB"

# 3) TAIFEX preflight/split checks (environment + session correctness)
say "taifex preflight"
bash scripts/m3_regression_taifex_preflight_v1.sh

say "taifex split"
bash scripts/m3_regression_taifex_split_v1.sh

# 4) OS-level governance / durability (audit/replay/reconcile/latency)
say "spec os"
bash scripts/m3_regression_spec_os_v1.sh

say "audit replay os"
bash scripts/m3_regression_audit_replay_os_v1.sh

say "reconcile os"
bash scripts/m3_regression_reconcile_os_v1.sh

say "latency backpressure os"
bash scripts/m3_regression_latency_backpressure_os_v1.sh

say "M3 REGRESSION SUITE v1 PASS"
