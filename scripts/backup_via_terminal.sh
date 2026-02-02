#!/usr/bin/env bash
set -euo pipefail

PROJ="$HOME/tmf_autotrader"
LOG_DIR="$PROJ/runtime/logs"
mkdir -p "$LOG_DIR"

# Headless: do NOT use osascript/Terminal. LaunchAgent should run deterministically.
exec /bin/bash -lc "$PROJ/scripts/backup_to_external.sh" >>"$LOG_DIR/backup.out.log" 2>>"$LOG_DIR/backup.err.log"
