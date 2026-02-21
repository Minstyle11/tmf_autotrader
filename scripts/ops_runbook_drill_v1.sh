#!/usr/bin/env bash
set -euo pipefail

# TMF AutoTrader — Runbook Drill v1 (Auto-Remediation skeleton)
# Evidence-first: writes artifacts under runtime/logs/
# Safe-by-default: DRY_RUN=1 means DO NOT restart anything

DRY_RUN="${DRY_RUN:-1}"
TS="$(date "+%Y-%m-%dT%H:%M:%S%z")"
LOG_DIR="runtime/logs"
mkdir -p "$LOG_DIR"
JSON_OUT="$LOG_DIR/runbook_drill_v1.latest.json"
LOG_OUT="$LOG_DIR/runbook_drill_v1.latest.log"

# Explicit whitelist (minimal). We will expand later via an OFFICIAL whitelist file.
TARGET_LABELS=(
  "com.tmf_autotrader.pm_tick"
  "com.tmf_autotrader.autorestart"
  "com.tmf_autotrader.daily_finance_close_pack_v1"
)

echo "[INFO] runbook_drill_v1 start ts=$TS dry_run=$DRY_RUN" | tee "$LOG_OUT"

check_label() {
  local label="$1"
  launchctl list 2>/dev/null | awk "{print \$3}" | grep -Fqx "$label" && echo "PRESENT" || echo "MISSING"
}

remediate_label() {
  local label="$1"
  local uid
  uid="$(id -u)"
  if [ "$DRY_RUN" = "1" ]; then
    echo "[DRY_RUN] would kickstart -k gui/${uid}/${label}" | tee -a "$LOG_OUT"
    return 0
  fi
  launchctl kickstart -k "gui/${uid}/${label}" | tee -a "$LOG_OUT" || true
}

# JSON lines payload for each target (then wrap into a list)
TMP_JSONL="$(mktemp -t tmf_runbook_drill.XXXXXX.jsonl)"
trap "rm -f \"$TMP_JSONL\"" EXIT

for label in "${TARGET_LABELS[@]}"; do
  before="$(check_label "$label")"
  echo "[CHECK] label=$label status=$before" | tee -a "$LOG_OUT"

  action="NONE"
  after="$before"
  if [ "$before" = "MISSING" ]; then
    action="REMEDIATE_KICKSTART"
    remediate_label "$label"
    after="$(check_label "$label")"
    echo "[VERIFY] label=$label after=$after" | tee -a "$LOG_OUT"
  fi

  python3 - <<PY >>"$TMP_JSONL"
import json
print(json.dumps({"label": "$label", "before": "$before", "action": "$action", "after": "$after"}))
PY
done

python3 - <<PY >"$JSON_OUT"
import json
from pathlib import Path
rows = [json.loads(line) for line in Path("$TMP_JSONL").read_text(encoding="utf-8").splitlines() if line.strip()]
payload = {
  "ts": "$TS",
  "dry_run": int("$DRY_RUN"),
  "targets": rows,
  "note": "Runbook drill v1 skeleton: detect->(dry-run)remediate->verify with explicit whitelist labels."
}
print(json.dumps(payload, indent=2, ensure_ascii=False))
PY

echo "[OK] runbook_drill_v1 wrote:" | tee -a "$LOG_OUT"
echo "[ARTIFACT] $JSON_OUT" | tee -a "$LOG_OUT"
echo "[ARTIFACT] $LOG_OUT"  | tee -a "$LOG_OUT"
echo "[OK] runbook_drill_v1 done" | tee -a "$LOG_OUT"
