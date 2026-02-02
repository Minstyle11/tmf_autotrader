#!/bin/bash
set -euo pipefail
cd "$HOME/tmf_autotrader"
echo "=== [m3 regression reject policy v1] start $(date -Iseconds) ==="

python3 - <<PY
from execution.reject_taxonomy import load_policy, decision_from_verdict

pol = load_policy("execution/reject_policy.yaml")

cases = [
  ({"ok": False, "code": "RISK_STOP_REQUIRED", "reason": "missing stop", "details": {}}, "REJECT"),
  ({"ok": False, "code": "RISK_DAILY_MAX_LOSS", "reason": "max loss hit", "details": {"today": -6000}}, "KILL"),
  ({"ok": False, "code": "RISK_CONSEC_LOSS_COOLDOWN", "reason": "cooldown", "details": {"mins": 5}}, "COOLDOWN"),
  ({"ok": False, "code": "SAFETY_FEED_STALE", "reason": "stale", "details": {"age": 999}}, "COOLDOWN"),
  ({"ok": False, "code": "BROKER_TIMEOUT", "reason": "timeout", "details": {}}, "RETRY"),
  ({"ok": True, "code": "OK", "reason": "pass", "details": {}}, "ALLOW"),
]

ok_all = True
for v, want in cases:
  d = decision_from_verdict(v, policy=pol)
  got = d.action
  ok = (got == want)
  print(f"[CASE] code={d.code} domain={d.domain} action={got} want={want} -> {'PASS' if ok else 'FAIL'}")
  if not ok:
    ok_all = False

if not ok_all:
  raise SystemExit(2)

print("[OK] reject policy regression PASS")
PY

echo "=== [m3 regression reject policy v1] PASS $(date -Iseconds) ==="
