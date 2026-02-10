#!/usr/bin/env bash
set -euo pipefail

cd "$HOME/tmf_autotrader"

TS="${1:-$(date '+%Y%m%d_%H%M%S')}"
OUTDIR="runtime/close_pack"
NAME="DAILY_FINANCE_CLOSE_PACK_${TS}"
WORK="$(mktemp -d "/tmp/${NAME}.XXXXXX")"
ROOT="$WORK/$NAME"

mkdir -p "$ROOT/files"

# ---- ALLOWLIST (best-effort copy; missing paths are OK) ----
copy_if_exists () {
  local src="$1"
  local dst_dir="$2"
  if [[ -e "$src" ]]; then
    mkdir -p "$dst_dir"
    if [[ -d "$src" ]]; then
      cp -a "$src" "$dst_dir/" || true
    else
      cp -p "$src" "$dst_dir/" || true
    fi
  fi
}

copy_if_exists "docs/board/PROJECT_BOARD.md"                 "$ROOT/files/docs/board"
copy_if_exists "docs/ops/OPS_INDEX.md"                      "$ROOT/files/docs/ops"
copy_if_exists "docs/ops/OPS_INDEX.md.sha256.txt"           "$ROOT/files/docs/ops"
copy_if_exists "docs/ops/OPS_SNAPSHOT_INDEXING_BIBLE_v1.md" "$ROOT/files/docs/ops"
copy_if_exists "docs/ops/OPS_SNAPSHOT_INDEXING_BIBLE_v1.md.sha256.txt" "$ROOT/files/docs/ops"
copy_if_exists "docs/ops/DAILY_FINANCE_CLOSE_PACK_BIBLE_v1.md" "$ROOT/files/docs/ops"
copy_if_exists "docs/ops/DAILY_FINANCE_CLOSE_PACK_BIBLE_v1.md.sha256.txt" "$ROOT/files/docs/ops"

# pm_tick logrotate snapshots (if exist)
copy_if_exists "docs/ops/PM_TICK_LOGROTATE_OFFICIAL_SNAPSHOT_20260204_110006.md" "$ROOT/files/docs/ops"
copy_if_exists "docs/ops/PM_TICK_LOGROTATE_OFFICIAL_SNAPSHOT_20260204_110006.md.sha256.txt" "$ROOT/files/docs/ops"
copy_if_exists "docs/ops/PM_TICK_LOGROTATE_RUNLOG_OFFICIAL_SNAPSHOT_20260204_112536.md" "$ROOT/files/docs/ops"
copy_if_exists "docs/ops/PM_TICK_LOGROTATE_RUNLOG_OFFICIAL_SNAPSHOT_20260204_112536.md.sha256.txt" "$ROOT/files/docs/ops"

# logs (include archive)
copy_if_exists "runtime/logs" "$ROOT/files/runtime"

# ---- MANIFEST (inner sha256 for all files) ----
cd "$ROOT/files"
LC_ALL=C find . -type f -print0 | LC_ALL=C sort -z | xargs -0 shasum -a 256 > "$ROOT/MANIFEST_SHA256_ALL_FILES.txt"

# ---- ZIP + SIDECAR SHA256 ----
cd "$WORK"
mkdir -p "$OUTDIR"
ZIP_PATH="$HOME/tmf_autotrader/$OUTDIR/${NAME}.zip"
zip -qry "$ZIP_PATH" "$NAME"
shasum -a 256 "$ZIP_PATH" > "${ZIP_PATH}.sha256.txt"

echo "[OK] built: $ZIP_PATH"
echo "[OK] sidecar: ${ZIP_PATH}.sha256.txt"
echo "[OK] workdir: $WORK"
