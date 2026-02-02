#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/tmf_autotrader"
DB="runtime/data/tmf_autotrader_v1.sqlite3"
LATEST="$(ls -1t runtime/data/raw_events_*.jsonl 2>/dev/null | head -n 1 || true)"
if [ -z "$LATEST" ]; then
  echo "[FATAL] no runtime/data/raw_events_*.jsonl found. Run recorder (MAX_SECONDS=6) first."
  exit 2
fi
echo "[INFO] latest=$LATEST"
. .venv/bin/activate
python -u src/data/store_sqlite_v1.py "$DB" "$LATEST"
echo "=== [OK] DB ready: $DB ==="
