#!/usr/bin/env bash
set -euo pipefail

PROJ="$HOME/tmf_autotrader"
STATE_DIR="$PROJ/runtime/handoff/state"
NEXT="$STATE_DIR/next_step.txt"

usage() {
  cat <<USAGE
Usage:
  ./scripts/set_next_step_v1.sh <KEY>

Supported KEY:
  M2_STEP1    -> start M2 Risk Engine v1 gates (daily max loss + consecutive losses cooldown + market-quality)
USAGE
}

KEY="${1:-}"
if [ -z "$KEY" ]; then usage; exit 2; fi

mkdir -p "$STATE_DIR"

case "$KEY" in
  M2_STEP1)
    cat > "$NEXT" <<'STEP'
bash <<'BASH'
set -euo pipefail
cd "$HOME/tmf_autotrader"

# M2 Risk Engine v1 — Step 1 (FOUNDATION)
# Goal: wire RiskEngineV1 into Paper OMS flow for paper-live path, and ensure all rejects are logged.
# Rule: additive only; do NOT break M0/M1.

# 1) Verify current demos still pass (sanity)
python3 -m py_compile src/risk/demo_risk_pretrade_v1.py src/risk/demo_risk_market_quality_v1.py
python3 src/risk/demo_risk_pretrade_v1.py
python3 src/risk/demo_risk_market_quality_v1.py

# 2) Next: integrate PaperOMSRiskWrapperV1 into the paper-live runner (create if missing),
#    ensuring meta carries stop_price + market snapshot (bid/ask/spread/atr/liquidity fields).
#    Keep append-only logging in DB (orders.meta_json already stores risk verdict).

echo "=== [TODO] Integrate risk wrapper into live/paper entrypoint (next commit) ==="
BASH
STEP
    ;;
  *)
    echo "[FATAL] unknown KEY: $KEY"
    usage
    exit 2
    ;;
esac

echo "=== [OK] wrote next_step ==="
echo "$NEXT"
