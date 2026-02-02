#!/usr/bin/env bash
set -euo pipefail

# Purpose:
#   Quarantine ONLY repo-root entries whose names start with a backtick: `*
#   - Never touches docs/, runtime/, src/, scripts/, etc. (find maxdepth=1)
#   - Generates MOVE_PLAN.md before moving
#   - Generates MOVE_LOG.md after moving
#   - Designed to be replay/audit friendly

PROJ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d_%H%M%S)"
QUAR="$PROJ/runtime/quarantine/scaffold_noise_${STAMP}"
PLAN="$QUAR/MOVE_PLAN.md"
LOG="$QUAR/MOVE_LOG.md"

mkdir -p "$QUAR"

items=()
while IFS= read -r -d '' p; do
  items+=("$p")
done < <(find "$PROJ" -maxdepth 1 -mindepth 1 -name '`*' -print0 2>/dev/null || true)

{
  echo "# MOVE_PLAN"
  echo "- time: $(date '+%F %T')"
  echo "- repo: $PROJ"
  echo "- quarantine: $QUAR"
  echo "- rule: move ONLY repo-root names matching: \`*"
  echo
  if [ "${#items[@]}" -eq 0 ]; then
    echo "## PLAN"
    echo "- (none) repo root has no backtick entries."
  else
    echo "## PLAN (count=${#items[@]})"
    for src in "${items[@]}"; do
      base="$(basename "$src")"
      echo "- MOVE: \`$base\` -> \`runtime/quarantine/$(basename "$QUAR")/$base\`"
    done
  fi
} > "$PLAN"

{
  echo "# MOVE_LOG"
  echo "- time: $(date '+%F %T')"
  echo "- repo: $PROJ"
  echo "- quarantine: $QUAR"
  echo "- plan: $PLAN"
  echo
} > "$LOG"

if [ "${#items[@]}" -eq 0 ]; then
  echo "[OK] no repo-root backtick entries. plan=$PLAN log=$LOG" | tee -a "$LOG"
  exit 0
fi

moved=0
for src in "${items[@]}"; do
  base="$(basename "$src")"
  dest="$QUAR/$base"
  if [ ! -e "$src" ]; then
    echo "[SKIP] missing src=$src" | tee -a "$LOG"
    continue
  fi
  if [ -e "$dest" ]; then
    echo "[WARN] dest exists, skip src=$src dest=$dest" | tee -a "$LOG"
    continue
  fi
  mv "$src" "$dest"
  echo "[MOVED] $src -> $dest" | tee -a "$LOG"
  moved=$((moved+1))
done

# Post-check: ensure repo root has no `* left
remain="$(find "$PROJ" -maxdepth 1 -mindepth 1 -name '`*' -print 2>/dev/null || true)"
if [ -n "$remain" ]; then
  echo "[FAIL] remain backtick entries under repo root:" | tee -a "$LOG"
  echo "$remain" | tee -a "$LOG"
  exit 2
fi

echo "[OK] moved=$moved plan=$PLAN log=$LOG" | tee -a "$LOG"
