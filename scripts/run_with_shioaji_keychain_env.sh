#!/bin/bash
set -euo pipefail

USER_NAME="${USER:-$(id -un)}"

get_kc() {
  local key="$1"
  security find-generic-password -a "$USER_NAME" -s "tmf_autotrader/$key" -w 2>/dev/null || true
}

# Export both TMF_* and SHIOAJI_* for compatibility with existing code
API="$(get_kc TMF_SHIOAJI_API_KEY)";   [ -n "$API" ] || API="$(get_kc SHIOAJI_API_KEY)"
SEC="$(get_kc TMF_SHIOAJI_SECRET_KEY)";[ -n "$SEC" ] || SEC="$(get_kc SHIOAJI_SECRET_KEY)"

export TMF_SHIOAJI_API_KEY="$API"
export TMF_SHIOAJI_SECRET_KEY="$SEC"
export SHIOAJI_API_KEY="$API"
export SHIOAJI_SECRET_KEY="$SEC"

# exec target script passed as args
exec "$@"
