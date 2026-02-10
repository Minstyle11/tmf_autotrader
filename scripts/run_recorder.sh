#!/usr/bin/env bash
set -euo pipefail

# --- env bootstrap (launchd-safe) ---
if [ -f "/tmf_autotrader/runtime/secrets/shioaji_env.sh" ]; then
  # shellcheck disable=SC1090
  source "/tmf_autotrader/runtime/secrets/shioaji_env.sh"
fi

set -euo pipefail
cd "$HOME/tmf_autotrader"
. .venv/bin/activate
./.venv/bin/python -u src/broker/shioaji_recorder.py
