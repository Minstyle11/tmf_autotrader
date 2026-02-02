#!/usr/bin/env bash
set -euo pipefail

PROJ="$HOME/tmf_autotrader"
STAMP="$(date +%F_%H%M%S)"
LOG_DIR="$PROJ/runtime/logs"
mkdir -p "$LOG_DIR"

TARGET_VOL=""

for v in /Volumes/*; do
  [ -d "$v" ] || continue
  if [ -f "$v/.tmf_autotrader_backup_target" ] && [ -w "$v" ]; then
    TARGET_VOL="$v"; break
  fi
done

if [ -z "$TARGET_VOL" ]; then
  for v in /Volumes/*; do
    [ -d "$v" ] || continue
    base="$(basename "$v")"
    case "$base" in
      "Macintosh HD"|"Macintosh HD - Data"|"Preboot"|"Recovery"|"Update"|"VM") continue;;
    esac
    if [ -w "$v" ]; then TARGET_VOL="$v"; break; fi
  done
fi

if [ -z "$TARGET_VOL" ]; then
  echo "[BACKUP][FAIL] No writable external volume found under /Volumes." | tee -a "$LOG_DIR/backup.err.log"
  echo "請插入外接硬碟；建議鎖定目標：touch /Volumes/<DRIVE>/.tmf_autotrader_backup_target" | tee -a "$LOG_DIR/backup.err.log"
  exit 2
fi

DEST_ROOT="$TARGET_VOL/tmf_autotrader_backups"
DEST="$DEST_ROOT/$STAMP"
mkdir -p "$DEST_ROOT"

rsync -a --delete \
  --exclude ".git/" \
  --exclude ".venv/" --exclude ".venv-*/" \
  --exclude "__pycache__/" --exclude "*.pyc" \
  --exclude ".DS_Store" \
  "$PROJ/" "$DEST/"

ln -sfn "$DEST" "$DEST_ROOT/latest"
echo "[BACKUP][OK] target=$TARGET_VOL dest=$DEST" | tee -a "$LOG_DIR/backup.out.log"
