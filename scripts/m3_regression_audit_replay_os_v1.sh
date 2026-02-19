#!/bin/bash
set -euo pipefail
cd "$HOME/tmf_autotrader"
echo "=== [m3 regression audit+replay os v1] start $(date -Iseconds) ==="

python3 - <<PY
import os, tempfile
from pathlib import Path
from datetime import datetime, timezone

from ops.audit.audit_recorder import append_event
from ops.replay.replay_runner import replay_jsonl

tmpdir = tempfile.mkdtemp(prefix="tmf_autotrader_audit_replay_regtest_")
logp = Path(tmpdir) / "audit.jsonl"

# deterministic minimal fixture (OFFICIAL-LOCKED)
append_event(str(logp), "ORDER_SUBMIT", {"symbol": "TMF", "side": "BUY", "qty": 1.0})
append_event(str(logp), "ORDER_REJECT", {"code": "RISK_STOP_REQUIRED", "reason": "missing stop"})

seen = {"n": 0, "kinds": []}
def handler(ev):
    seen["n"] += 1
    seen["kinds"].append(ev.get("kind"))

repo = Path(os.path.expanduser("~/tmf_autotrader"))
outdir = repo / "runtime" / "handoff" / "state"
outdir.mkdir(parents=True, exist_ok=True)

# Write LATEST as the single truth-source (robust)
latest_json = outdir / "replay_report_latest.json"
latest_md   = outdir / "replay_report_latest.md"

res = replay_jsonl(
    str(logp),
    handler=handler,
    deterministic=True,
    report_json_path=str(latest_json),
    report_md_path=str(latest_md),
)
print("[INFO] replay_result =", res)

assert res.ok and res.code == "OK", res
assert seen["n"] == 2, seen
assert seen["kinds"] == ["ORDER_SUBMIT", "ORDER_REJECT"], seen

# Snapshot (best-effort, should NOT break hardgate if filesystem hiccup)
ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
snap_json = outdir / f"replay_report_{ts}.json"
snap_md   = outdir / f"replay_report_{ts}.md"
try:
    snap_json.write_text(latest_json.read_text(encoding="utf-8"), encoding="utf-8")
    snap_md.write_text(latest_md.read_text(encoding="utf-8"), encoding="utf-8")
    print("[OK] wrote replay report snapshot:", str(snap_json))
except Exception as e:
    print("[WARN] snapshot write failed (non-fatal):", e)

print("[OK] m3 audit+replay regression PASS:", str(logp))
print("[OK] wrote replay report latest:", str(latest_json))
PY

echo "=== [m3 regression audit+replay os v1] PASS $(date -Iseconds) ==="

echo "=== [GATE] spec-diff stopper (OFFICIAL-LOCKED) ===";
bash scripts/m3_regression_spec_diff_stopper_v1.sh;

echo "=== [GATE] reject policy (OFFICIAL-LOCKED) ===";
bash scripts/m3_regression_reject_policy_v1.sh;

echo "=== [GATE] reconcile OS (OFFICIAL-LOCKED) ===";
bash scripts/m3_regression_reconcile_os_v1.sh;
echo "=== [GATE] reject stats (OFFICIAL-LOCKED) ===";
bash scripts/m3_regression_reject_stats_v1.sh;
