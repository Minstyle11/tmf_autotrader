#!/usr/bin/env bash
set -euo pipefail
# [AUTO] generate NEW_WINDOW_OPENING_PROMPT (ULTRA) before packing
python3 scripts/gen_new_window_opening_prompt_ultra_zh.py || true


PROJ="$HOME/tmf_autotrader"
STAMP="$(date +%Y%m%d_%H%M%S)"
PACK_NAME="tmf_autotrader_windowpack_ultra_${STAMP}"
WORK_BASE="$PROJ/runtime/handoff/_pack_work_${STAMP}"
PACK_ROOT="$WORK_BASE/${PACK_NAME}"
LATEST_DIR="$PROJ/runtime/handoff/latest"

mkdir -p "$PACK_ROOT/handoff" "$PACK_ROOT/state" "$PACK_ROOT/repo" "$LATEST_DIR"

NOW="$(date "+%Y-%m-%d %H:%M:%S")"


# 0) OPS Audit + Env Rebuild HardGate (MUST PASS before packing)
./scripts/ops_audit_hardgate_v1.sh
./scripts/ops_env_rebuild_hardgate_v1.sh

# Copy latest audit report into pack (evidence)
LATEST_AUDIT="$(ls -1t "$PROJ/runtime/handoff/state"/audit_report_*.md 2>/dev/null | head -n 1 || true)"
if [ -n "$LATEST_AUDIT" ] && [ -f "$LATEST_AUDIT" ]; then
  cp -f "$LATEST_AUDIT" "$PACK_ROOT/state/audit_report_latest.md"
fi

# Copy latest env rebuild report into pack (evidence)
LATEST_ENV="$(ls -1t "$PROJ/runtime/handoff/state"/env_rebuild_report_*.md 2>/dev/null | head -n 1 || true)"
if [ -n "$LATEST_ENV" ] && [ -f "$LATEST_ENV" ]; then
  cp -f "$LATEST_ENV" "$PACK_ROOT/state/env_rebuild_report_latest.md"
fi

# 1) Copy handoff artifacts (outside repo, authoritative)
mkdir -p "$PROJ/docs/handoff"
# NOTE: NEVER truncate repo handoff log during packing (append-only contract)
if [ -f "$PROJ/docs/handoff/HANDOFF_LOG.md" ]; then
  cp -f "$PROJ/docs/handoff/HANDOFF_LOG.md" "$PACK_ROOT/handoff/HANDOFF_LOG.md"
else
  : > "$PACK_ROOT/handoff/HANDOFF_LOG.md"
fi


# 2) Copy state (authoritative outside-repo state)
mkdir -p "$PROJ/runtime/handoff/state"
# NOTE: NEVER truncate repo next_step during packing (mutable but preserved)
if [ -f "$PROJ/runtime/handoff/state/next_step.txt" ]; then
  cp -f "$PROJ/runtime/handoff/state/next_step.txt" "$PACK_ROOT/state/next_step.txt"
else
  : > "$PACK_ROOT/state/next_step.txt"
fi

if [ -f "$PROJ/runtime/handoff/state/latest_state.json" ]; then
  cp -f "$PROJ/runtime/handoff/state/latest_state.json" "$PACK_ROOT/state/latest_state.json"
fi

# 2.5) New-window OneShot HardGate SOP (pack-root convenience copy)
if [ -f "$PROJ/runtime/handoff/state/NEW_WINDOW_ONESHOT_HARDGATE_SOP.txt" ]; then
  cp -f "$PROJ/runtime/handoff/state/NEW_WINDOW_ONESHOT_HARDGATE_SOP.txt" "$PACK_ROOT/state/NEW_WINDOW_ONESHOT_HARDGATE_SOP.txt"
fi

# Copy NEW_WINDOW_CLIPBOARD (for zero-thinking new-window start)
if [ -f "$PROJ/runtime/handoff/state/NEW_WINDOW_CLIPBOARD_ULTRA_ZH.txt" ]; then
  cp -f "$PROJ/runtime/handoff/state/NEW_WINDOW_CLIPBOARD_ULTRA_ZH.txt" "$PACK_ROOT/state/NEW_WINDOW_CLIPBOARD_ULTRA_ZH.txt"
  if [ -f "$PROJ/runtime/handoff/state/NEW_WINDOW_CLIPBOARD_ULTRA_ZH.txt.sha256.txt" ]; then
    cp -f "$PROJ/runtime/handoff/state/NEW_WINDOW_CLIPBOARD_ULTRA_ZH.txt.sha256.txt" "$PACK_ROOT/state/NEW_WINDOW_CLIPBOARD_ULTRA_ZH.txt.sha256.txt"
  fi
fi


# 3) Repo snapshot (preserve paths under repo/ via --relative)
cd "$PROJ"
rsync -a --delete \
  --exclude ".git/" --exclude ".venv/" --exclude ".venv-*/" --exclude "__pycache__/" --exclude "*.pyc" --exclude ".DS_Store" \
  --relative \
  ./src ./scripts ./configs ./docs ./runtime/logs ./runtime/handoff/state \
  "$PACK_ROOT/repo/" 2>/dev/null || true

# 4) LaunchAgents (outside repo)
mkdir -p "$PACK_ROOT/repo/LaunchAgents"
for f in \
  "$HOME/Library/LaunchAgents/com.tmf_autotrader.backup.plist" \
  "$HOME/Library/LaunchAgents/com.tmf_autotrader.pm_tick.plist" \
  "$HOME/Library/LaunchAgents/com.tmf_autotrader.autorestart.plist" \
  "$HOME/Library/LaunchAgents/com.tmf_autotrader.handoff_tick.plist"
do
  if [ -f "$f" ]; then
    cp -f "$f" "$PACK_ROOT/repo/LaunchAgents/"
  fi
done

# 5) Final opening prompt
OPEN_FINAL_REPO="$PROJ/docs/handoff/NEW_WINDOW_OPENING_PROMPT_FINAL.md"
OPEN_DRAFT_REPO="$PROJ/docs/handoff/NEW_WINDOW_OPENING_PROMPT_DRAFT.md"
OPEN_FINAL="$PACK_ROOT/NEW_WINDOW_OPENING_PROMPT_FINAL.md"
if [ -f "$OPEN_FINAL_REPO" ]; then
  cp -f "$OPEN_FINAL_REPO" "$OPEN_FINAL"
elif [ -f "$OPEN_DRAFT_REPO" ]; then
  cp -f "$OPEN_DRAFT_REPO" "$OPEN_FINAL"
else
  cat > "$OPEN_FINAL" <<EOM
# NEW WINDOW OPENING PROMPT (AUTO-FALLBACK)
Generated: ${NOW}
(Missing both FINAL and DRAFT; use repo/docs/handoff/ to regenerate.)
EOM
fi

# 6) Handoff ULTRA summary
HANDOFF_MD="$PACK_ROOT/HANDOFF_ULTRA.md"
cat > "$HANDOFF_MD" <<EOM
# TMF AutoTrader — Window Handoff ULTRA
Generated: ${NOW}

## What this pack contains
- repo/: conservative snapshot of project code + docs + runtime/logs + runtime/handoff/state (paths preserved)
- handoff/: append-only HANDOFF_LOG.md
- state/: latest_state.json + next_step.txt
- NEW_WINDOW_OPENING_PROMPT_FINAL.md: latest opening prompt (from docs/handoff draft)
## Integrity
- MANIFEST_SHA256_ALL_FILES.txt at pack root
- ZIP + .sha256 sidecar under runtime/handoff/latest
EOM

# 7) Manifest (fail fast if newline in path)
python3 - <<PY
import hashlib
from pathlib import Path

root = Path("${PACK_ROOT}")
out = root / "MANIFEST_SHA256_ALL_FILES.txt"

def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024*1024), b""):
            h.update(chunk)
    return h.hexdigest()

pairs = []
for p in sorted(root.rglob("*")):
    if p.is_dir():
        continue
    rel = p.relative_to(root).as_posix()
    if "\\n" in rel or "\\r" in rel:
        raise SystemExit(f"[FATAL] newline in path: {rel!r}")
    pairs.append((sha256(p), rel))

out.write_text("\\n".join([f"{h}  {rel}" for (h, rel) in pairs]) + "\\n", encoding="utf-8")
print(f"[OK] wrote {out} files={len(pairs)}")
PY

# 8) Zip + sha256 sidecar
ZIP="$LATEST_DIR/TMF_AutoTrader_WindowPack_ULTRA_${STAMP}.zip"
( cd "$WORK_BASE" && /usr/bin/zip -qr "$ZIP" "$PACK_NAME" )
SHA_FILE="${ZIP}.sha256.txt"
# NOTE: sidecar MUST contain basename only (so shasum -c works when running inside latest dir)
( cd "$(dirname "$ZIP")" && bn="$(basename "$ZIP")" && shasum -a 256 "$bn" > "$(basename "$SHA_FILE")" )
echo "=== [OK] BUILT ==="
ls -l "$ZIP" "$SHA_FILE"
echo "=== [UNZIP -l top35] ==="
unzip -l "$ZIP" | head -n 35 || true

REPO_ROOT="${REPO_ROOT:-$(pwd -P)}"

# [HARD-REQ] opening prompt must be included in ULTRA windowpack (v18 one-truth)
# If this fails, the pack is NOT acceptable for seamless handoff.
_require_opening_prompt_in_latest_zip() {
  local z
  z="$(ls -t "$REPO_ROOT/runtime/handoff/latest"/TMF_AutoTrader_WindowPack_ULTRA_*.zip 2>/dev/null | head -n 1 || true)"
  if [ -z "$z" ]; then
    echo "[FAIL] cannot locate latest ULTRA zip under runtime/handoff/latest" >&2
    return 11
  fi
  unzip -l "$z" | grep -E "NEW_WINDOW_OPENING_PROMPT_ULTRA_ZH\.md(\.sha256\.txt)?$" >/dev/null || {
    echo "[FAIL] latest ULTRA zip missing NEW_WINDOW_OPENING_PROMPT_ULTRA_ZH.md (+ sha256). zip=$z" >&2
    return 12
  }

  unzip -l "$z" | grep -E "NEW_WINDOW_CLIPBOARD_ULTRA_ZH\.txt(\.sha256\.txt)?$" >/dev/null || {
    echo "[FAIL] latest ULTRA zip missing NEW_WINDOW_CLIPBOARD_ULTRA_ZH.txt (+ sha256). zip=$z" >&2
    return 13
  }
  echo "[OK] hard-req opening prompt present in zip=$z"
}


_require_opening_prompt_in_latest_zip
# [HARD-REQ] handoff SOP bible must be included in ULTRA windowpack (One-Truth)
_require_handoff_sop_bible_in_latest_zip() {
  local z
  z="$(ls -t "$REPO_ROOT/runtime/handoff/latest"/TMF_AutoTrader_WindowPack_ULTRA_*.zip 2>/dev/null | head -n 1 || true)"
  if [ -z "$z" ]; then
    echo "[FAIL] cannot locate latest ULTRA zip under runtime/handoff/latest" >&2
    return 31
  fi
  unzip -l "$z" | grep -E "repo/docs/bibles/HANDOFF_SOP_OFFICIAL_BIBLE_v1\.md(\.sha256\.txt)?$" >/dev/null || {
    echo "[FAIL] latest ULTRA zip missing repo/docs/bibles/HANDOFF_SOP_OFFICIAL_BIBLE_v1.md (+ sha256). zip=$z" >&2
    return 32
  }
  echo "[OK] hard-req handoff SOP bible present in zip=$z"
}

_require_handoff_sop_bible_in_latest_zip


# [HARD-REQ] env rebuild evidence must be included in ULTRA windowpack (seamless rebuildability)
_require_env_rebuild_report_in_latest_zip() {
  local z
  z="$(ls -t "$REPO_ROOT/runtime/handoff/latest"/TMF_AutoTrader_WindowPack_ULTRA_*.zip 2>/dev/null | head -n 1 || true)"
  if [ -z "$z" ]; then
    echo "[FAIL] cannot locate latest ULTRA zip under runtime/handoff/latest" >&2
    return 31
  fi
  unzip -l "$z" | grep -E "(^|/)(env_rebuild_report_latest\.md)$" >/dev/null || {
    echo "[FAIL] latest ULTRA zip missing env_rebuild_report_latest.md (state evidence). zip=$z" >&2
    return 32
  }
  echo "[OK] hard-req env rebuild evidence present in zip=$z"
}

_require_env_rebuild_report_in_latest_zip

# [HARD-REQ] OneShot HardGate SOP must be included in ULTRA windowpack (for zero-thinking new-window acceptance)
_require_oneshot_hardgate_sop_in_latest_zip() {
  local z
  z="$(ls -t "$REPO_ROOT/runtime/handoff/latest"/TMF_AutoTrader_WindowPack_ULTRA_*.zip 2>/dev/null | head -n 1 || true)"
  if [ -z "$z" ]; then
    echo "[FAIL] cannot locate latest ULTRA zip under runtime/handoff/latest" >&2
    return 21
  fi
  unzip -l "$z" | grep -E "NEW_WINDOW_ONESHOT_HARDGATE_SOP\.txt$" >/dev/null || {
    echo "[FAIL] latest ULTRA zip missing NEW_WINDOW_ONESHOT_HARDGATE_SOP.txt. zip=$z" >&2
    return 22
  }
  echo "[OK] hard-req oneshot hardgate sop present in zip=$z"
}

_require_oneshot_hardgate_sop_in_latest_zip

# [HARD-REQ] autostart doc must be included in ULTRA windowpack (seamless upload-only handoff)
_require_autostart_in_latest_zip() {
  local z
  z="$(ls -t "$REPO_ROOT/runtime/handoff/latest"/TMF_AutoTrader_WindowPack_ULTRA_*.zip 2>/dev/null | head -n 1 || true)"
  if [ -z "$z" ]; then
    echo "[FAIL] cannot locate latest ULTRA zip under runtime/handoff/latest" >&2
    return 21
  fi
  unzip -l "$z" | grep -E "NEW_WINDOW_AUTOSTART_ULTRA_ZH\.md(\.sha256\.txt)?$" >/dev/null || {
    echo "[FAIL] latest ULTRA zip missing NEW_WINDOW_AUTOSTART_ULTRA_ZH.md (+ sha256). zip=$z" >&2
    return 22
  }
  echo "[OK] hard-req autostart present in zip=$z"
}
