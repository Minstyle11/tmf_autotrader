#!/usr/bin/env bash
set -euo pipefail

PROJ="$HOME/tmf_autotrader"
cd "$PROJ"

TS="$(date '+%F %T')"
MSG="${1:-pm_tick}"

# --- append changelog (append-only) ---
mkdir -p "$PROJ/docs/board"
echo "- [$TS] $MSG" >> "$PROJ/docs/board/CHANGELOG.md"

# Optional: print a tiny status line (will go to LaunchAgent out log)
echo "[pm_tick] $TS msg=$MSG"
