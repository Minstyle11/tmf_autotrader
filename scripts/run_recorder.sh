#!/usr/bin/env bash
set -euo pipefail

# --- env bootstrap (launchd-safe) ---
# 1) Prefer repo-local secrets file (recommended for production/launchd)
SECRETS="$HOME/tmf_autotrader/runtime/secrets/shioaji_env.sh"
if [ -f "$SECRETS" ]; then
  # shellcheck disable=SC1090
  . "$SECRETS"
fi

# 2) Also support .env (dev convenience; launchd does NOT inherit interactive shell env)
for f in "$HOME/tmf_autotrader/.env" "$HOME/.tmf_autotrader.env"; do
  if [ -f "$f" ]; then
    set -a
    # shellcheck disable=SC1090
    . "$f"
    set +a
  fi
done

cd "$HOME/tmf_autotrader"
. .venv/bin/activate
./.venv/bin/python -u src/broker/shioaji_recorder.py
