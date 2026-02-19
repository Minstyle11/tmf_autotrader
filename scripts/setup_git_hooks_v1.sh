#!/usr/bin/env bash
set -euo pipefail

# CWD-agnostic: derive project root from this script location, allow override.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
PROJ="${PROJ:-"$(cd "$SCRIPT_DIR/.." && pwd -P)"}"

if ! command -v git >/dev/null 2>&1; then
  echo "[SKIP] git not found"
  exit 0
fi

if [ ! -d "$PROJ/.git" ]; then
  echo "[SKIP] not a git repo: $PROJ"
  exit 0
fi

# Use git -C to avoid any dependence on current working directory.
git -C "$PROJ" config --local core.hooksPath .githooks

echo "[OK] core.hooksPath set to .githooks (repo=$PROJ)"
