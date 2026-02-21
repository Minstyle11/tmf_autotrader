#!/usr/bin/env bash
set -euo pipefail

PROJ=\"${PROJ:-$HOME/tmf_autotrader}\"
# [AUTO] generate NEW_WINDOW_OPENING_PROMPT (ULTRA) before packing
python3 scripts/gen_new_window_opening_prompt_ultra_zh.py || true

cd "$HOME/tmf_autotrader"

TS="$(date +%Y%m%d_%H%M%S)"
OUT="runtime/handoff/state/audit_report_${TS}.md"
mkdir -p "$(dirname "$OUT")"

{
  echo "# TMF AutoTrader — OPS Audit HardGate v1"
  echo "Generated: $(date '+%Y-%m-%d %H:%M:%S')"
  echo
  echo "## 1) Dangerous filenames (newline / CR)"
  bad="$(python3 - <<'PY'
import os
root=os.path.expanduser("~/tmf_autotrader")
bad=[]
for dp, dn, fn in os.walk(root):
  for n in fn:
    if "\n" in n or "\r" in n:
      bad.append(os.path.join(dp,n))
print("\n".join(bad))
PY
)"
  if [ -n "${bad:-}" ]; then
    echo "FATAL: newline/CR in filenames:"
    echo '```'
    echo "$bad"
    echo '```'
    exit 2
  else
    echo "- OK (none)"
  fi
  echo

  echo "## 2) bash syntax check (scripts/*.sh)"
  echo '```'
  failed=0
  while IFS= read -r f; do
    if ! bash -n "$f"; then
      failed=1
    fi
  done < <(find scripts -type f -name "*.sh" -print | sort)
  echo '```'
  if [ "$failed" -ne 0 ]; then
    echo "FATAL: bash -n failed"
    exit 3
  else
    echo "- OK"
  fi
  echo

  echo "## 3) python compile (src/**/*.py)"
  echo '```'
  python3 - <<'PY'
import compileall
ok = compileall.compile_dir("src", quiet=1)
raise SystemExit(0 if ok else 4)
PY
  echo '```'
  echo "- OK"
  echo

  echo "## 4) sqlite integrity_check (if db found)"
  if command -v sqlite3 >/dev/null 2>&1; then
    db="$(find runtime -maxdepth 5 -type f \( -name "*.sqlite" -o -name "*.db" -o -name "*.sqlite3" \) | head -n 1 || true)"
    if [ -n "${db:-}" ]; then
      echo "- DB: $db"
      echo '```'
      sqlite3 "$db" "PRAGMA integrity_check;"
      echo '```'
    else
      echo "- SKIP (no db file under runtime/)"
    fi
  else
    echo "- SKIP (sqlite3 not installed)"
  fi
  echo

  echo "## 5) launchd quick status"
  echo '```'
  launchctl list 2>/dev/null | grep -F "com.tmf_autotrader." || true
  echo '```'
  echo

  echo "## 6) git status (if repo)"
  if command -v git >/dev/null 2>&1 && [ -d "$PROJ/.git" ]; then
    echo '```'
    git -C "$PROJ" status --porcelain=v1 || true
    echo '```'
  else
    echo "- SKIP (not a git repo)"
  fi
  echo
  echo "## 7) latest ULTRA pack self-verify (if exists)"
  latest_zip="$(ls -1t runtime/handoff/latest/TMF_AutoTrader_WindowPack_ULTRA_*.zip 2>/dev/null | head -n 1 || true)"
  if [ -n "${latest_zip:-}" ]; then
    echo "- ZIP: ${latest_zip}"
    echo "\`\`\`"
    if [ -f "${latest_zip}.sha256.txt" ]; then
      ( cd "$(dirname "${latest_zip}")" && shasum -a 256 -c "$(basename "${latest_zip}").sha256.txt" )
    else
      echo "[FATAL] missing zip sidecar: ${latest_zip}.sha256.txt"
      exit 7
    fi

    tmpdir="$(mktemp -d)"
    /usr/bin/unzip -q "${latest_zip}" -d "${tmpdir}"
    root="$(find "${tmpdir}" -maxdepth 1 -type d \( -name "tmf_autotrader_windowpack_ultra_*" -o -name "windowpack_ultra_*" \) | head -n 1 || true)"
    if [ -z "${root:-}" ]; then
      echo "[FATAL] cannot locate unpack root under: ${tmpdir}"
      exit 8
    fi
    if [ ! -f "${root}/MANIFEST_SHA256_ALL_FILES.txt" ]; then
      echo "[FATAL] missing manifest in unpack root: ${root}"
      exit 9
    fi
    ( cd "${root}" && shasum -a 256 -c MANIFEST_SHA256_ALL_FILES.txt )
    echo "\`\`\`"
    echo "- OK"
  else
    echo "- SKIP (no TMF_AutoTrader_WindowPack_ULTRA_*.zip under runtime/handoff/latest)"
  fi

  echo "## 8) M2 regression suite v1 (risk + market-quality + paper-live)"
  echo '```'
  out=""
  rc=0
  if out="$(bash scripts/m2_regression_suite_v1.sh 2>&1)"; then
    rc=0
  else
    rc=$?
  fi
  echo "$out"
  echo '```'
  if [ "${rc:-0}" -ne 0 ]; then
    echo "FATAL: m2_regression_suite_v1 failed rc=$rc"
    exit 10
  else
    echo "- OK"
  fi
  echo

  echo "## 9) M3 OS chaos drill v1 (latency/backpressure)"
  echo '```'
  out=""
  rc=0
  if out="$(bash scripts/ops_chaos_drill_v1.sh 2>&1)"; then
    rc=0
  else
    rc=$?
  fi
  echo "$out"
  echo '```'
  echo "### Chaos drill artifacts sha256"
  echo '```'
  shasum -a 256 runtime/logs/chaos_drill_v1.latest.json || true
  shasum -a 256 runtime/logs/chaos_drill_v1.latest.log  || true
  echo '```'
  echo


  echo "## 10) M3 OS runbook drill v1 (auto-remediation)"
  out="$(DRY_RUN=1 bash scripts/ops_runbook_drill_v1.sh 2>&1 || true)"
  echo '```'
  echo "$out"
  echo '```'
  echo "### Runbook drill artifacts sha256"
  echo '```'
  shasum -a 256 runtime/logs/runbook_drill_v1.latest.json || true
  shasum -a 256 runtime/logs/runbook_drill_v1.latest.log  || true
  echo '```'
  echo
  if [ "${rc:-0}" -ne 0 ]; then
    echo "FATAL: ops_chaos_drill_v1 failed rc=$rc"
    exit 11
  else
    echo "- OK"
  fi
  echo

  echo "## RESULT"
  echo "- PASS"
} > "$OUT"

echo "[OK] wrote audit report: $OUT"

cp -f "$OUT" "runtime/handoff/state/audit_report_latest.md"
echo "[OK] wrote audit latest: runtime/handoff/state/audit_report_latest.md"
# record to handoff log
./scripts/handoff_tick.sh "ops_audit_hardgate_v1_${TS}" >/dev/null 2>&1 || true
echo "[OK] handoff_tick recorded"

# [HARD-REQ][AUDIT] opening prompt must be included in latest ULTRA windowpack (v18 one-truth)
_append_hardreq_opening_prompt_to_audit_reports() {
  set -euo pipefail

  local z latest_ts_report latest_report
  z="$(ls -t runtime/handoff/latest/TMF_AutoTrader_WindowPack_ULTRA_*.zip 2>/dev/null | head -n 1 || true)"
  latest_ts_report="$(ls -t runtime/handoff/state/audit_report_*.md 2>/dev/null | head -n 1 || true)"
  latest_report="runtime/handoff/state/audit_report_latest.md"

  if [ -z "$z" ]; then
    echo "[FAIL][AUDIT] cannot locate latest ULTRA zip under runtime/handoff/latest" >&2
    return 31
  fi
  if [ ! -f "$latest_report" ]; then
    echo "[FAIL][AUDIT] missing audit_report_latest.md at $latest_report" >&2
    return 32
  fi

  # hard-req check (must fail audit if missing)
  unzip -l "$z" | egrep "NEW_WINDOW_OPENING_PROMPT_ULTRA_ZH\.md(\.sha256\.txt)?$" >/dev/null || {
    echo "[FAIL][AUDIT] latest ULTRA zip missing NEW_WINDOW_OPENING_PROMPT_ULTRA_ZH.md (+ sha256). zip=$z" >&2
    return 33
  }

  # Append section to audit reports (idempotent: only append if section not present)
  for f in "$latest_report" "$latest_ts_report"; do
    [ -n "${f:-}" ] && [ -f "${f:-}" ] || continue
    if ! egrep -q "^## \[HARD-REQ\] Opening Prompt in Latest ULTRA ZIP" "$f"; then
      {
        echo ""
        echo "## [HARD-REQ] Opening Prompt in Latest ULTRA ZIP"
        echo "- zip: \`$z\`"
        echo "- required files:"
        echo "  - \`runtime/handoff/state/NEW_WINDOW_OPENING_PROMPT_ULTRA_ZH.md\`"
        echo "  - \`runtime/handoff/state/NEW_WINDOW_OPENING_PROMPT_ULTRA_ZH.md.sha256.txt\`"
        echo "- check: unzip list contains opening prompt ✔"
      } >> "$f"
    fi
  done

  echo "[OK][AUDIT] hard-req opening prompt appended to audit report(s)"
}
_append_hardreq_opening_prompt_to_audit_reports


echo "=== [OS] audit+replay + spec-diff + reject + reconcile (OFFICIAL-LOCKED) ===";
bash scripts/m3_regression_audit_replay_os_v1.sh;
