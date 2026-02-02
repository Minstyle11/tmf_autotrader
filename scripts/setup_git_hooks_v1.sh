#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

# Use versioned hooks directory
git config --local core.hooksPath .githooks

# Ensure hook is executable (Git ignores non-executable hooks)
chmod +x .githooks/pre-push 2>/dev/null || true

echo "[OK] core.hooksPath=$(git config --local --get core.hooksPath)"
ls -l .githooks/pre-push || true
