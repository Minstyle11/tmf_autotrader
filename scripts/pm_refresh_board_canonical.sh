#!/bin/bash
set -euo pipefail

# --- repo-root portable (CI-safe) ---
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [ -n "$REPO_ROOT" ] && [ -d "$REPO_ROOT" ]; then
  cd "$REPO_ROOT"
else
  SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
  cd "$(cd "$SCRIPT_DIR/.." && pwd -P)"
fi

# --- single-instance lock (atomic mkdir) ---
LOCKDIR="runtime/locks"
LOCK="$LOCKDIR/pm_refresh_board_canonical.lock"
mkdir -p "$LOCKDIR"
if mkdir "$LOCK" 2>/dev/null; then
  trap 'rmdir "$LOCK" >/dev/null 2>&1 || true' EXIT
else
  # already running -> exit cleanly
  echo "[SKIP] pm_refresh_board_canonical already running"
  exit 0
fi

# --- run canonical refresh and ALWAYS emit something ---
out="$(python3 scripts/pm_refresh_board_v2.py 2>&1 || true)"

line="$(printf "%s\n" "$out" | grep -F "[OK] canonical board progress:" | tail -n 1 || true)"
if [ -n "$line" ]; then
  echo "$line"
else
  echo "[WARN] pm_refresh_board_v2.py produced no canonical progress line; showing last 30 lines for diagnostics"
  printf "%s\n" "$out" | tail -n 30
fi

exit 0
