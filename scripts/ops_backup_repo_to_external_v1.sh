#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${HOME}/tmf_autotrader"
VOL_NAME="${TMF_BACKUP_VOLUME_NAME:-TMF_BACKUP}"

# Pick target volume safely
target_vol=""
if [ -d "/Volumes/${VOL_NAME}" ]; then
  target_vol="/Volumes/${VOL_NAME}"
else
  # best-effort: pick first external-ish volume (avoid common system volumes)
  for d in /Volumes/*; do
    bn="$(basename "$d")"
    case "$bn" in
      "Macintosh HD"|"Macintosh HD - Data"|"Preboot"|"Recovery"|"VM") continue ;;
    esac
    if [ -d "$d" ]; then
      target_vol="$d"
      break
    fi
  done
fi

if [ -z "${target_vol}" ] || [ ! -d "${target_vol}" ]; then
  echo "[FATAL] cannot locate backup target volume. Create /Volumes/TMF_BACKUP or set TMF_BACKUP_VOLUME_NAME." >&2
  exit 2
fi

TS="$(date +%Y%m%d_%H%M%S)"
DEST="${target_vol}/tmf_autotrader_backup/repo_snapshot_${TS}"

# Pre-create DEST to avoid rsync mkpath failures under launchd
mkdir -p "${DEST}"
mkdir -p "${target_vol}/tmf_autotrader_backup"

# NOTE: Constitution rule: do NOT delete any repo files. This script only reads repo and writes to external drive.
# Use rsync for incremental copy; avoid --delete to be extra safe.
# -a: archive; -E: preserve extended attributes on macOS (best-effort)
rsync -aE \
  --exclude ".venv/" \
  --exclude "runtime/data/" \
  --exclude "runtime/handoff/_pack_work_*/" \
  "${REPO_ROOT}/" "${DEST}/"

echo "[OK] backup done: ${DEST}"
