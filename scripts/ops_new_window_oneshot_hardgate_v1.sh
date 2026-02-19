#!/usr/bin/env bash
set -euo pipefail

# TMF AutoTrader — New Window OneShot HardGate v1
# Usage:
#   ./scripts/ops_new_window_oneshot_hardgate_v1.sh [path_to_zip]
# If zip not provided, it will auto-detect newest TMF_AutoTrader_WindowPack_ULTRA_*.zip from:
#   1) current directory
#   2) ~/Downloads
#   3) runtime/handoff/latest (if running inside repo)

say() { printf '%s\n' "$*"; }
die() { say "[FAIL] $*" >&2; exit 1; }

detect_zip() {
  local z="${1:-}"
  if [ -n "${z}" ]; then
    [ -f "${z}" ] || die "zip not found: ${z}"
    say "${z}"
    return 0
  fi

  local cand=""
  # (1) current dir
  cand="$(ls -1t ./TMF_AutoTrader_WindowPack_ULTRA_*.zip 2>/dev/null | head -n 1 || true)"
  if [ -n "${cand}" ]; then say "${cand}"; return 0; fi

  # (2) Downloads
  cand="$(ls -1t "$HOME/Downloads"/TMF_AutoTrader_WindowPack_ULTRA_*.zip 2>/dev/null | head -n 1 || true)"
  if [ -n "${cand}" ]; then say "${cand}"; return 0; fi

  # (3) repo latest (if present)
  cand="$(ls -1t runtime/handoff/latest/TMF_AutoTrader_WindowPack_ULTRA_*.zip 2>/dev/null | head -n 1 || true)"
  if [ -n "${cand}" ]; then say "${cand}"; return 0; fi

  die "cannot auto-detect TMF_AutoTrader_WindowPack_ULTRA_*.zip (try providing zip path arg)"
}

main() {
  local zip sidecar zip_dir zip_base
  zip="$(detect_zip "${1:-}")"
  sidecar="${zip}.sha256.txt"
  [ -f "${sidecar}" ] || die "missing zip sha256 sidecar: ${sidecar}"

  zip_dir="$(cd "$(dirname "${zip}")" && pwd)"
  zip_base="$(basename "${zip}")"

  say "=== [A] ZIP sha256 verify ==="
  say "[ZIP] ${zip_dir}/${zip_base}"
    # Robust verify: accept sidecar that records either basename OR repo-relative path.
  # We compare only the hash (1st column) against the actual zip sha256.
  local expected actual
  expected="$(/usr/bin/awk 'NR==1{print $1}' "${sidecar}")"
  actual="$(/usr/bin/shasum -a 256 "${zip_dir}/${zip_base}" | /usr/bin/awk '{print $1}')"
  [ "${expected}" = "${actual}" ] || die "zip sha256 mismatch: expected=${expected} actual=${actual}"

  say "[PASS] zip sha256 OK"

  say "=== [B] unzip to temp ==="
  local stamp tmp unpack_root
  stamp="$(date +%Y%m%d_%H%M%S)"
  tmp="/tmp/tmf_autotrader_newwindow_unpack_${stamp}"
  mkdir -p "${tmp}"
  /usr/bin/unzip -q "${zip_dir}/${zip_base}" -d "${tmp}"

  unpack_root="$(find "${tmp}" -mindepth 1 -maxdepth 1 -type d | head -n 1 || true)"
  [ -n "${unpack_root}" ] || die "unzip produced no root dir under ${tmp}"
  say "[ROOT] ${unpack_root}"

  say "=== [C] Pack HardGate (manifest) ==="
  [ -f "${unpack_root}/MANIFEST_SHA256_ALL_FILES.txt" ] || die "missing manifest at pack root: ${unpack_root}/MANIFEST_SHA256_ALL_FILES.txt"
  ( cd "${unpack_root}" && /usr/bin/shasum -a 256 -c MANIFEST_SHA256_ALL_FILES.txt ) >/dev/null
  say "[PASS] manifest sha256 all files OK"

  say "=== [D] Hard-Req spot-check (sealed files) ==="
  local req1 req2 req3 req4 req5 req6
  req1="${unpack_root}/repo/runtime/handoff/state/NEW_WINDOW_OPENING_PROMPT_ULTRA_ZH.md"
  req2="${unpack_root}/repo/runtime/handoff/state/NEW_WINDOW_OPENING_PROMPT_ULTRA_ZH.md.sha256.txt"
  req3="${unpack_root}/repo/docs/handoff/NEW_WINDOW_OPENING_PROMPT_FINAL.md"
  req4="${unpack_root}/repo/docs/bibles/HANDOFF_SOP_OFFICIAL_BIBLE_v1.md"
  req5="${unpack_root}/repo/runtime/handoff/state/env_rebuild_report_latest.md"
  req6="${unpack_root}/repo/runtime/handoff/state/NEW_WINDOW_CLIPBOARD_ULTRA_ZH.txt"

  [ -f "${req1}" ] || die "missing: ${req1}"
  [ -f "${req2}" ] || die "missing: ${req2}"
  [ -f "${req3}" ] || die "missing: ${req3}"
  [ -f "${req4}" ] || die "missing: ${req4}"
  [ -f "${req5}" ] || die "missing: ${req5}"
  [ -f "${req6}" ] || die "missing: ${req6}"

  local h1 h2
  h1="$(head -n 1 "${req3}" || true)"
  h2="$(head -n 1 "${req4}" || true)"
  [ "${h1}" = "# NEW WINDOW OPENING PROMPT (FINAL, AUTO-UPDATED)" ] || die "FINAL header mismatch: ${h1}"
  case "${h2}" in
    "# HANDOFF_SOP_OFFICIAL_v"*) : ;;
    *) die "HANDOFF SOP bible header unexpected: ${h2}" ;;
  esac
  say "[PASS] sealed files + headers OK"

  say "=== [E] Env Rebuild Evidence (read-only) ==="
  say "[ENV_REPORT] ${req5}"
  sed -n '1,120p' "${req5}" || true

  say "=== [F] Next step ==="
  local ns="${unpack_root}/state/next_step.txt"
  [ -f "${ns}" ] || die "missing: ${ns}"
  say "[NEXT_STEP_FILE] ${ns}"
  cat "${ns}" || true


  say "=== [D0] WEB RESEARCH EVIDENCE HARDGATE (FAIL-fast) ==="
  local d0_sh="${unpack_root}/repo/scripts/ops_web_research_evidence_hardgate_v1.sh"
  local d0_ev="${unpack_root}/repo/runtime/handoff/state/web_research_evidence_latest.md"
  [ -x "${d0_sh}" ] || die "missing hardgate script in pack: ${d0_sh}"
  "${d0_sh}" "${d0_ev}"

say "=== [RESULT] PASS (pack+env+prompt+sop+clipboard) ==="
say "=== [AUTO] show OPENING_PROMPT (first 220 lines) ==="
if [ -n "${unpack_root:-}" ] && [ -f "${unpack_root}/repo/runtime/handoff/state/NEW_WINDOW_OPENING_PROMPT_ULTRA_ZH.md" ]; then
  ( cd "${unpack_root}/repo" && sed -n "1,220p" runtime/handoff/state/NEW_WINDOW_OPENING_PROMPT_ULTRA_ZH.md ) || true
else
  say "[WARN] opening prompt not found under unpack. unpack_root=${unpack_root:-<empty>}"
fi
say "=== [AUTO] show NEXT_STEP ==="
if [ -n "${unpack_root:-}" ] && [ -f "${unpack_root}/state/next_step.txt" ]; then
  sed -n "1,220p" "${unpack_root}/state/next_step.txt" || true
else
  say "[WARN] next_step.txt not found under unpack. unpack_root=${unpack_root:-<empty>}"
fi

  say "[INFO] unpack kept at: ${tmp}"
}

main "$@"
