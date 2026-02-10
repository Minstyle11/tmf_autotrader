#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/tmf_autotrader"

LOG_DIR="runtime/logs"
mkdir -p "$LOG_DIR"
# --- LOG ROTATION (auto) ---
# rotate autorestart logs to avoid unbounded growth (keep last N archives)
ROT_MB="${TMF_AUTORESTART_LOG_ROTATE_MB:-5}"
KEEP="${TMF_AUTORESTART_LOG_KEEP:-30}"

rotate_if_big() {
  local f="$1"
  [ -f "$f" ] || return 0
  local sz
  sz=$(wc -c < "$f" 2>/dev/null || echo 0)
  if [ "$sz" -ge $((ROT_MB*1024*1024)) ]; then
    local ts
    ts="$(date +%Y%m%d_%H%M%S)_$$"
    mv "$f" "${f}.${ts}" 2>/dev/null || true
    : > "$f"
  fi
}

trim_archives() {
  # keep newest $KEEP rotated archives per log base (e.g. autorestart.out.log)
  local base="$1"
  local list
  list=$(ls -1t "$LOG_DIR/${base}."* 2>/dev/null || true)
  [ -n "$list" ] || return 0
  local n=0
  while IFS= read -r fp; do
    [ -n "$fp" ] || continue
    n=$((n+1))
    if [ "$n" -gt "$KEEP" ]; then
      rm -f "$fp" 2>/dev/null || true
    fi
  done <<< "$list"
}


LOCK="/tmp/tmf_autotrader_autorestart.lock"
if mkdir "$LOCK" 2>/dev/null; then
  cleanup() {
  rc=$?
  # --- LOG ROTATION (auto; always run on exit; keep last N archives) ---
  ROT_MB="${TMF_AUTORESTART_LOG_ROTATE_MB:-5}"
  KEEP="${TMF_AUTORESTART_LOG_KEEP:-30}"

  rotate_if_big() {
    f="$1"
    [ -f "$f" ] || return 0
    sz=$(wc -c < "$f" 2>/dev/null || echo 0)
    # If forcing rotate (ROT_MB=0), skip creating empty archives
    if [ "${ROT_MB}" = "0" ] && [ "$sz" -eq 0 ]; then
      return 0
    fi
    if [ "$sz" -ge $((ROT_MB*1024*1024)) ]; then
      ts="$(date +%Y%m%d_%H%M%S)_$$"
      mv "$f" "${f}.${ts}" 2>/dev/null || true
      : > "$f"
    fi
  }

  trim_archives() {
    base="$1"  # e.g. autorestart.out.log
    n=0
    for fp in $(ls -1t "$LOG_DIR/${base}."* 2>/dev/null || true); do
      n=$((n+1))
      if [ "$n" -gt "$KEEP" ]; then
        rm -f "$fp" 2>/dev/null || true
      fi
    done
  }

  rotate_if_big "$LOG_DIR/autorestart.out.log"
  rotate_if_big "$LOG_DIR/autorestart.err.log"
  rotate_if_big "$LOG_DIR/autorestart.pipeline.log"
  rotate_if_big "$LOG_DIR/autorestart.last_healthcheck.log"

  trim_archives "autorestart.out.log"
  trim_archives "autorestart.err.log"
  trim_archives "autorestart.pipeline.log"
  trim_archives "autorestart.last_healthcheck.log"

  rmdir "$LOCK" 2>/dev/null || true
  exit "$rc"
}
trap cleanup EXIT
else
  echo "[autorestart] lock busy, skip"
  exit 0

# --- rotate/trim AFTER lock (avoid concurrent rotate races) ---
rotate_if_big "$LOG_DIR/autorestart.out.log"
rotate_if_big "$LOG_DIR/autorestart.err.log"
rotate_if_big "$LOG_DIR/autorestart.pipeline.log"
rotate_if_big "$LOG_DIR/autorestart.last_healthcheck.log"

trim_archives "autorestart.out.log"
trim_archives "autorestart.err.log"
trim_archives "autorestart.pipeline.log"
trim_archives "autorestart.last_healthcheck.log"

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
