#!/usr/bin/env bash
set -euo pipefail
# [AUTO] generate NEW_WINDOW_OPENING_PROMPT (ULTRA) before packing
python3 scripts/gen_new_window_opening_prompt_ultra_zh.py || true

PROJ="$HOME/tmf_autotrader"
MSG="${1:-auto}"
NOW="$(date "+%Y-%m-%d %H:%M:%S")"

LOG="$PROJ/docs/handoff/HANDOFF_LOG.md"
DRAFT="$PROJ/docs/handoff/NEW_WINDOW_OPENING_PROMPT_DRAFT.md"
FINAL="$PROJ/docs/handoff/NEW_WINDOW_OPENING_PROMPT_FINAL.md"
NEXT_STEP="$PROJ/runtime/handoff/state/next_step.txt"

mkdir -p "$(dirname "$LOG")" "$(dirname "$DRAFT")" "$(dirname "$FINAL")" "$(dirname "$NEXT_STEP")"
touch "$LOG" "$NEXT_STEP"

BOARD_HEAD="$(sed -n "1,35p" "$PROJ/docs/board/PROJECT_BOARD.md" 2>/dev/null || true)"
CHANGELOG_TAIL="$(tail -n 15 "$PROJ/docs/board/CHANGELOG.md" 2>/dev/null || true)"

GIT_SUMMARY=""
if command -v git >/dev/null 2>&1 && [ -d "$PROJ/.git" ]; then
  GIT_SUMMARY="$(cd "$PROJ" && git status --porcelain=v1 2>/dev/null || true)"
fi

NEXT_STEP_HEAD="$(sed -n "1,12p" "$NEXT_STEP" 2>/dev/null || true)"
NEXT_STEP_FULL="$(cat "$NEXT_STEP" 2>/dev/null || true)"

append_block () {
  local title="$1"
  local body="${2:-}"
  echo "### $title"
  echo
  echo '```text'
  printf "%s\n" "$body"
  echo '```'
  echo
}

# Append-only handoff log
{
  echo ""
  echo "## [$NOW] $MSG"
  echo ""
  append_block "Board (head)" "$BOARD_HEAD"
  append_block "Changelog (tail)" "$CHANGELOG_TAIL"
  append_block "Working tree (git status --porcelain)" "$GIT_SUMMARY"
  append_block "Next terminal step (head)" "$NEXT_STEP_HEAD"
} >> "$LOG"

# Overwrite DRAFT with latest snapshot (DRAFT is allowed to rewrite)
{
  echo "# NEW WINDOW OPENING PROMPT (FINAL, AUTO-UPDATED)"
  echo
  echo "## Current status (Board head)"
  echo
  echo '```text'
  printf "%s\n" "$BOARD_HEAD"
  echo '```'
  echo
  echo "## Latest changes (Changelog tail)"
  echo
  echo '```text'
  printf "%s\n" "$CHANGELOG_TAIL"
  echo '```'
  echo
  echo "## Working tree (git status --porcelain)"
  echo
  echo '```text'
  printf "%s\n" "$GIT_SUMMARY"
  echo '```'
  echo
  echo "## Next terminal step (runtime/handoff/state/next_step.txt)"
  echo
  echo '```text'
  printf "%s\n" "$NEXT_STEP_FULL"
  echo '```'
  echo
  echo "## Rules (must follow)"
  echo "- One terminal command per turn."
  echo "- Append-only logs; no silent rewrites."
  echo "- One-click ZIP only when assistant signals capacity risk."
} > "$DRAFT"

# Overwrite FINAL with latest snapshot (FINAL is allowed to rewrite; it's the handoff entrypoint)
{
  echo "# NEW WINDOW OPENING PROMPT (FINAL, AUTO-UPDATED)"
  echo
  echo "## Current status (Board head)"
  echo
  echo '```text'
  printf "%s\n" "$BOARD_HEAD"
  echo '```'
  echo
  echo "## Latest changes (Changelog tail)"
  echo
  echo '```text'
  printf "%s\n" "$CHANGELOG_TAIL"
  echo '```'
  echo
  echo "## Working tree (git status --porcelain)"
  echo
  echo '```text'
  printf "%s\n" "$GIT_SUMMARY"
  echo '```'
  echo
  echo "## Next terminal step (runtime/handoff/state/next_step.txt)"
  echo
  echo '```text'
  printf "%s\n" "$NEXT_STEP_FULL"
  echo '```'
  echo
  echo "## Rules (must follow)"
  echo "- One terminal command per turn."
  echo "- Append-only logs; no silent rewrites."
  echo "- One-Doc/One-Truth: TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18.md."
} > "$FINAL"


echo "[handoff_tick] $NOW msg=$MSG"

# [HARD-REQ] opening prompt must be included in ULTRA windowpack (v18 one-truth)
# --- BEGIN_SEAL_CONDITIONAL_V1 ---
_maybe_seal_opening_prompt_into_latest_zip() {
  # Guard against recursion/loop
  if [ "${TMF_SEAL_RUNNING:-0}" = "1" ]; then
    echo "[OK] seal skipped (TMF_SEAL_RUNNING=1)"
    return 0
  fi

  local prompt="runtime/handoff/state/NEW_WINDOW_OPENING_PROMPT_ULTRA_ZH.md"
  local prompt_sha="$prompt.sha256.txt"

  if [ ! -f "$prompt" ] || [ ! -f "$prompt_sha" ]; then
    echo "[FAIL] opening prompt missing: $prompt (+ sha256). Cannot seal." >&2
    return 2
  fi

  local z
  z="$(ls -t runtime/handoff/latest/TMF_AutoTrader_WindowPack_ULTRA_*.zip 2>/dev/null | head -n 1 || true)"

  # If no zip, build one
  if [ -z "$z" ]; then
    echo "[STEP] seal: no latest ULTRA zip -> build fresh"
    TMF_SEAL_RUNNING=1 bash scripts/mk_windowpack_ultra.sh >/dev/null
    return 0
  fi

  # If zip missing opening prompt, rebuild
  if ! unzip -l "$z" | egrep "NEW_WINDOW_OPENING_PROMPT_ULTRA_ZH\.md(\.sha256\.txt)?$" >/dev/null; then
    echo "[STEP] seal: latest zip missing opening prompt -> rebuild fresh. zip=$z"
    TMF_SEAL_RUNNING=1 bash scripts/mk_windowpack_ultra.sh >/dev/null
    return 0
  fi

  # If prompt newer than zip, rebuild (zip must be >= prompt)
  python3 - <<'PY2' "$z"
from pathlib import Path
import sys
prompt = Path("runtime/handoff/state/NEW_WINDOW_OPENING_PROMPT_ULTRA_ZH.md")
z = Path(sys.argv[1])
if prompt.stat().st_mtime > z.stat().st_mtime:
    print("[STEP] seal: prompt newer than zip -> rebuild fresh")
    sys.exit(10)
print("[OK] seal not needed (latest zip already fresh vs prompt)")
PY2
  rc=$?
  if [ "$rc" = "10" ]; then
    TMF_SEAL_RUNNING=1 bash scripts/mk_windowpack_ultra.sh >/dev/null
  elif [ "$rc" != "0" ]; then
    return "$rc"
  fi

  return 0
}
# --- END_SEAL_CONDITIONAL_V1 ---

_require_opening_prompt_in_latest_zip() {
  local z
  z="$(ls -t runtime/handoff/latest/TMF_AutoTrader_WindowPack_ULTRA_*.zip 2>/dev/null | head -n 1 || true)"
  if [ -z "$z" ]; then
    echo "[FAIL] cannot locate latest ULTRA zip under runtime/handoff/latest" >&2
    return 21
  fi
  unzip -l "$z" | egrep "NEW_WINDOW_OPENING_PROMPT_ULTRA_ZH\.md(\.sha256\.txt)?$" >/dev/null || {
    echo "[FAIL] latest ULTRA zip missing NEW_WINDOW_OPENING_PROMPT_ULTRA_ZH.md (+ sha256). zip=$z" >&2
    return 22
  }
  echo "[OK] hard-req opening prompt present in zip=$z"
}




_maybe_seal_opening_prompt_into_latest_zip
_require_opening_prompt_in_latest_zip
