#!/usr/bin/env bash
set -euo pipefail

PROJ="$HOME/tmf_autotrader"
STAMP="$(date "+%Y%m%d_%H%M%S")"
OUT="runtime/handoff/state/env_rebuild_report_${STAMP}.md"
LATEST="runtime/handoff/state/env_rebuild_report_latest.md"

mkdir -p "$(dirname "$OUT")"

note () { printf "%s\n" "$*"; }

emit_kv () {
  local k="$1"; shift
  local v="${1:-}"
  printf -- "- %s: %s\n" "$k" "$v"
}

must_cmd () {
  local c="$1"
  if ! command -v "$c" >/dev/null 2>&1; then
    echo "[FATAL] missing command: $c" >&2
    return 10
  fi
}

pyver_ok () {
  local pv
  pv="$(python3 -c 'import sys; print(".".join(map(str,sys.version_info[:3])))' 2>/dev/null || true)"
  if [ -z "$pv" ]; then
    echo "[FATAL] python3 not runnable" >&2
    return 11
  fi
  # Accept 3.9.x as baseline (per project rule). If not 3.9, mark FATAL.
  if ! python3 -c 'import sys; sys.exit(0 if sys.version_info[:2]==(3,9) else 1)'; then
    echo "[FATAL] python3 must be 3.9.x (baseline). got=$pv" >&2
    return 12
  fi
  echo "$pv"
}

hash_file () {
  local f="$1"
  if [ -f "$f" ]; then
    shasum -a 256 "$f" | awk '{print $1}'
  else
    echo ""
  fi
}

# ----------------- checks -----------------
RC=0
{
  echo "# ENV REBUILD HARDGATE REPORT (v1)"
  echo
  emit_kv "timestamp" "$(date "+%F %T")"
  emit_kv "project_root" "$PROJ"
  echo

  echo "## 1) Host + shell"
  echo
  emit_kv "whoami" "$(whoami)"
  emit_kv "uname" "$(uname -a | sed 's/  */ /g')"
  emit_kv "shell" "${SHELL:-}"
  echo

  echo "## 2) Required commands"
  echo
  for c in python3 git shasum unzip; do
    if command -v "$c" >/dev/null 2>&1; then
      emit_kv "$c" "$(command -v "$c")"
    else
      emit_kv "$c" "MISSING"
      RC=13
    fi
  done
  echo

  echo "## 3) Python baseline (must be 3.9.x)"
  echo
  pv="$(pyver_ok)" || RC=$?
  emit_kv "python3_version" "${pv:-ERROR}"
  echo

  echo "## 4) Repo sanity"
  echo
  if [ -d "$PROJ/.git" ]; then
    emit_kv ".git" "OK"
    emit_kv "git_head" "$(cd "$PROJ" && git rev-parse --short HEAD 2>/dev/null || true)"
    emit_kv "git_status_porcelain_lines" "$(cd "$PROJ" && git status --porcelain=v1 2>/dev/null | wc -l | tr -d ' ')"
  else
    emit_kv ".git" "MISSING"
    RC=14
  fi
  echo

  echo "## 5) venv + dependency fingerprint"
  echo
  VENV="$PROJ/.venv"
  if [ -x "$VENV/bin/python" ]; then
    emit_kv "venv" "OK ($VENV)"
    emit_kv "venv_python" "$("$VENV/bin/python" -c 'import sys; print(".".join(map(str,sys.version_info[:3])))' 2>/dev/null || true)"
    # pip freeze snapshot (no secrets)
    tmp="$(mktemp)"
    "$VENV/bin/python" -m pip --version >/dev/null 2>&1 || true
    "$VENV/bin/python" -m pip freeze 2>/dev/null | LC_ALL=C sort > "$tmp" || true
    fp="$(shasum -a 256 "$tmp" | awk '{print $1}')"
    rm -f "$tmp"
    emit_kv "pip_freeze_sha256" "${fp:-}"
  else
    emit_kv "venv" "MISSING (.venv/bin/python not found)"
    RC=15
  fi
  echo

  echo "## 6) Critical project files (existence only)"
  echo
  # DO NOT print secret contents. Existence + sha256 only.
  critical=(
    "docs/bibles/TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18.md"
    "docs/bibles/TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18.md.sha256.txt"
    "runtime/handoff/state/NEW_WINDOW_OPENING_PROMPT_ULTRA_ZH.md"
    "runtime/handoff/state/NEW_WINDOW_OPENING_PROMPT_ULTRA_ZH.md.sha256.txt"
    "configs/instruments.yaml"
    "configs/secrets/shioaji.env"
    "scripts/mk_windowpack_ultra.sh"
    "scripts/ops_audit_hardgate_v1.sh"
  )
  for f in "${critical[@]}"; do
    if [ -f "$PROJ/$f" ]; then
      emit_kv "$f" "OK sha256=$(hash_file "$PROJ/$f")"
    else
      emit_kv "$f" "MISSING"
      RC=16
    fi
  done
  echo

  echo "## 7) LaunchAgents quick check (existence only)"
  echo
  la_dir="$HOME/Library/LaunchAgents"
  emit_kv "LaunchAgents_dir" "$la_dir"
  if [ -d "$la_dir" ]; then
    # just count + list tmf_autotrader plists, do not load/unload here
    n_all="$(ls -1 "$la_dir" 2>/dev/null | wc -l | tr -d ' ')"
    n_tmf="$(ls -1 "$la_dir"/com.tmf_autotrader*.plist 2>/dev/null | wc -l | tr -d ' ')"
    emit_kv "LaunchAgents_count" "$n_all"
    emit_kv "tmf_autotrader_plists" "$n_tmf"
  else
    emit_kv "LaunchAgents_dir" "MISSING"
    RC=17
  fi
  echo

  echo "## 8) Verdict"
  echo
  if [ "${RC:-0}" = "0" ]; then
    echo "- RESULT: PASS"
  else
    echo "- RESULT: FAIL rc=${RC}"
  fi
  echo
} > "$OUT"

cp -f "$OUT" "$LATEST"

echo "[OK] wrote: $OUT"
echo "[OK] wrote: $LATEST"

# hardgate exit
if [ "${RC:-0}" != "0" ]; then
  echo "[FATAL] env hardgate failed rc=$RC" >&2
  exit "$RC"
fi

echo "[PASS] env hardgate OK"
