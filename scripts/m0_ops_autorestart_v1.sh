#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/tmf_autotrader"

LOG_DIR="runtime/logs"
mkdir -p "$LOG_DIR"

LOCK="/tmp/tmf_autotrader_autorestart.lock"
if mkdir "$LOCK" 2>/dev/null; then
  trap 'rmdir "$LOCK" 2>/dev/null || true' EXIT
else
  echo "[autorestart] lock busy, skip"
  exit 0
fi

# Decide STRICT_SESSION by local time bucket:
# DAY 08:30–14:00, NIGHT 15:00–05:00
HHMM="$(date +%H%M)"
STRICT=0
if [ "$HHMM" -ge 0830 ] && [ "$HHMM" -lt 1400 ]; then
  STRICT=1
elif [ "$HHMM" -ge 1500 ] || [ "$HHMM" -lt 0500 ]; then
  STRICT=1
fi

TS="$(date '+%F %T')"
echo "[autorestart] $TS strict=$STRICT start" >> "$LOG_DIR/autorestart.out.log"

set +e
STRICT_SESSION="$STRICT" ./scripts/m0_healthcheck_v1.sh >"$LOG_DIR/autorestart.last_healthcheck.log" 2>&1
RC=$?
set -e

if [ "$RC" -eq 0 ]; then
  echo "[autorestart] $TS healthcheck OK (rc=0)" >> "$LOG_DIR/autorestart.out.log"
  exit 0
fi

echo "[autorestart] $TS healthcheck FAIL rc=$RC -> run m0_pipeline_one.sh (self-heal)" >> "$LOG_DIR/autorestart.err.log"

# Self-heal: run one pipeline pass (recorder+ingest+norm+bars)
MAX_SECONDS="${MAX_SECONDS:-30}" ./scripts/m0_pipeline_one.sh >> "$LOG_DIR/autorestart.pipeline.log" 2>&1 || true

set +e
STRICT_SESSION="$STRICT" ./scripts/m0_healthcheck_v1.sh >>"$LOG_DIR/autorestart.last_healthcheck.log" 2>&1
RC2=$?
set -e

TS2="$(date '+%F %T')"
if [ "$RC2" -eq 0 ]; then
  echo "[autorestart] $TS2 self-heal OK" >> "$LOG_DIR/autorestart.out.log"
  exit 0
else
  echo "[autorestart] $TS2 self-heal STILL FAIL rc=$RC2" >> "$LOG_DIR/autorestart.err.log"
  exit 1
fi
