#!/bin/bash
set -euo pipefail

cd "$HOME/tmf_autotrader"

# --- single-instance lock (atomic mkdir) ---
LOCKDIR="runtime/locks"
LOCK="$LOCKDIR/pm_refresh_board_canonical.lock"
mkdir -p "$LOCKDIR"
if mkdir "$LOCK" 2>/dev/null; then
  trap 'rmdir "$LOCK" >/dev/null 2>&1 || true' EXIT
else
  # already running -> exit cleanly
  exit 0
fi

# Canonical chain -> emit EXACTLY ONE canonical line for LaunchAgent logs
python3 scripts/pm_refresh_board_v2.py | grep -F "[OK] canonical board progress:" | tail -n 1
