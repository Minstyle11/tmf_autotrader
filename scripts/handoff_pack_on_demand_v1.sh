#!/usr/bin/env bash
set -euo pipefail
# [AUTO] generate NEW_WINDOW_OPENING_PROMPT (ULTRA) before packing
python3 scripts/gen_new_window_opening_prompt_ultra_zh.py || true


PROJ="${PROJ:-$HOME/tmf_autotrader}"
MODE="${1:-}"
TS="$(date "+%Y%m%d_%H%M%S")"

OUT_DIR="$PROJ/runtime/handoff/latest"
WORK_DIR="$PROJ/runtime/handoff/_pack_work_$TS"
PKG_DIR="$WORK_DIR/tmf_autotrader_windowpack_ultra_$TS"

ZIP_BASENAME="TMF_AutoTrader_WindowPack_ULTRA_${TS}.zip"
ZIP_PATH="$OUT_DIR/$ZIP_BASENAME"
ZIP_SHA="$ZIP_PATH.sha256.txt"
MF_PATH="$PKG_DIR/MANIFEST_SHA256_ALL_FILES.txt"
OPENING_FINAL="$PKG_DIR/NEW_WINDOW_OPENING_PROMPT_FINAL.md"

mkdir -p "$OUT_DIR" "$WORK_DIR" "$PKG_DIR"

# ---- build FINAL opening prompt from latest DRAFT + state json ----
DRAFT="$PROJ/docs/handoff/NEW_WINDOW_OPENING_PROMPT_DRAFT.md"
STATE="$PROJ/runtime/handoff/state/latest_state.json"
NEXT_STEP="$PROJ/runtime/handoff/state/next_step.txt"

{
  echo "# NEW WINDOW OPENING PROMPT (FINAL, GENERATED)"
  echo
  echo "## What this pack contains"
  echo "- This ZIP is an on-demand handoff pack."
  echo "- It includes current repo snapshot (selected), board/changelog, handoff logs, and machine-readable state."
  echo
  echo "## Machine-readable state"
  if [ -f "$STATE" ]; then
    echo "\`\`\`json"
    cat "$STATE"
    echo "\`\`\`"
  else
    echo "(missing) runtime/handoff/state/latest_state.json"
  fi
  echo
  echo "## Next terminal step (mutable file content)"
  if [ -f "$NEXT_STEP" ]; then
    echo "\`\`\`text"
    cat "$NEXT_STEP"
    echo "\`\`\`"
  else
    echo "(missing) runtime/handoff/state/next_step.txt"
  fi
  echo
  echo "## Current project status (from DRAFT)"
  if [ -f "$DRAFT" ]; then
    sed -n "1,240p" "$DRAFT" || true
  else
    echo "(missing) docs/handoff/NEW_WINDOW_OPENING_PROMPT_DRAFT.md"
  fi
  echo
  echo "## Rules (hard)"
  echo "- One terminal command per turn."
  echo "- Append-only logs; no silent rewrites."
  echo "- One-click ZIP packing only when assistant signals capacity risk."
} > "$OPENING_FINAL"

# ---- copy snapshot into PKG_DIR (exclude heavy/ephemeral) ----
# We copy the whole repo structure, but exclude runtime/data, logs, venv, git, caches.
if command -v rsync >/dev/null 2>&1; then
  rsync -a \
    --exclude ".git/" \
    --exclude ".venv/" \
    --exclude "__pycache__/" \
    --exclude "*.pyc" \
    --exclude "runtime/data/" \
    --exclude "runtime/logs/" \
    --exclude "runtime/handoff/_pack_work_" \
    --exclude "runtime/handoff/latest/" \
    "$PROJ/" "$PKG_DIR/repo/"
else
  mkdir -p "$PKG_DIR/repo/"
  tar -C "$PROJ" -cf - . \
    --exclude ".git" \
    --exclude ".venv" \
    --exclude "__pycache__" \
    --exclude "*.pyc" \
    --exclude "runtime/data" \
    --exclude "runtime/logs" \
    --exclude "runtime/handoff/_pack_work_" \
    --exclude "runtime/handoff/latest" \
    | tar -C "$PKG_DIR/repo" -xf -
fi

# Ensure key handoff/state artifacts are present at top-level too (quick access)
mkdir -p "$PKG_DIR/state" "$PKG_DIR/handoff"
[ -f "$STATE" ] && cp -f "$STATE" "$PKG_DIR/state/latest_state.json" || true
[ -f "$NEXT_STEP" ] && cp -f "$NEXT_STEP" "$PKG_DIR/state/next_step.txt" || true
[ -f "$PROJ/docs/handoff/HANDOFF_LOG.md" ] && cp -f "$PROJ/docs/handoff/HANDOFF_LOG.md" "$PKG_DIR/handoff/HANDOFF_LOG.md" || true

# ---- build manifest sha256 (root=PKG_DIR; exclude self-line for hardgate) ----
python3 - "$PKG_DIR" <<'PY'
import hashlib, sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
mf = root / 'MANIFEST_SHA256_ALL_FILES.txt'

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

items = []
for p in sorted(root.rglob('*')):
    if p.is_file():
        rel = p.relative_to(root).as_posix()
        if p.name == mf.name:  # exclude ANY manifest file to avoid hardgate self-line
            continue
        items.append((rel, sha256_file(p)))

mf.write_text(''.join([f"{h}  {rel}\n" for (rel,h) in items]), encoding='utf-8')
print('[OK] wrote', mf, 'files=', len(items))
PY

# ---- ensure top-level manifest for hardgate (root must have MANIFEST_SHA256_ALL_FILES.txt) ----
if [ ! -f "$PKG_DIR/MANIFEST_SHA256_ALL_FILES.txt" ] && [ -f "$PKG_DIR/repo/MANIFEST_SHA256_ALL_FILES.txt" ]; then
  cp -f "$PKG_DIR/repo/MANIFEST_SHA256_ALL_FILES.txt" "$PKG_DIR/MANIFEST_SHA256_ALL_FILES.txt"
fi


# ---- dryrun mode (no zip) ----
if [ "$MODE" = "--dryrun" ]; then
  echo "=== [DRYRUN] pack root ==="
  echo "$PKG_DIR"
  echo "=== [DRYRUN] top-level files ==="
  (cd "$PKG_DIR" && ls -la | sed -n "1,120p") || true
  exit 0
fi

# ---- zip + sha256 sidecar ----
( cd "$WORK_DIR" && /usr/bin/zip -qr "$ZIP_PATH" "$(basename "$PKG_DIR")" )

SHA="$(python3 - "$ZIP_PATH" <<'PY'
import hashlib, sys
p = sys.argv[1]
h = hashlib.sha256()
with open(p,"rb") as f:
  for chunk in iter(lambda: f.read(1024*1024), b""):
    h.update(chunk)
print(h.hexdigest())
PY
)"


echo "$SHA  $ZIP_PATH" > "$ZIP_SHA"

echo "=== [OK] PACK BUILT ==="
echo "ZIP=$ZIP_PATH"
echo "SHA=$ZIP_SHA"
