#!/usr/bin/env bash
set -euo pipefail

# 1) Run canonical board sync (must be deterministic / idempotent)
python3 scripts/board_sync_v1.py

# 2) Board must not have uncommitted drift after sync
if ! git diff --exit-code -- docs/board/PROJECT_BOARD.md >/dev/null; then
  echo "[FATAL] PROJECT_BOARD.md drift detected after board_sync_v1.py."
  echo "        This means something wrote progress lines outside AUTO blocks, or sync rules changed."
  echo "        Fix by running: python3 scripts/board_sync_v1.py (and commit the result)."
  git --no-pager diff -- docs/board/PROJECT_BOARD.md || true
  exit 2
fi

echo "[OK] board guard PASS"
