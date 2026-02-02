#!/bin/bash
set -euo pipefail
cd "$HOME/tmf_autotrader"
echo "=== [m3 regression audit+replay os v1] start $(date -Iseconds) ==="

python3 - <<'PY'
import tempfile
from pathlib import Path

from ops.audit.audit_recorder import append_event
from ops.replay.replay_runner import replay_jsonl

tmpdir = tempfile.mkdtemp(prefix="tmf_autotrader_audit_replay_regtest_")
logp = Path(tmpdir) / "audit.jsonl"

append_event(str(logp), "ORDER_SUBMIT", {"symbol": "TMF", "side": "BUY", "qty": 1.0})
append_event(str(logp), "ORDER_REJECT", {"code": "RISK_STOP_REQUIRED", "reason": "missing stop"})

seen = {"n": 0, "kinds": []}
def handler(ev):
    seen["n"] += 1
    seen["kinds"].append(ev.get("kind"))

res = replay_jsonl(str(logp), handler=handler)
print("[INFO] replay_result =", res)

assert res.ok and res.code == "OK", res
assert seen["n"] == 2, seen
assert seen["kinds"] == ["ORDER_SUBMIT", "ORDER_REJECT"], seen

print("[OK] m3 audit+replay regression PASS:", str(logp))
PY

echo "=== [m3 regression audit+replay os v1] PASS $(date -Iseconds) ==="
