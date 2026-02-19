#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== [m3 regression reject stats v1] start $(date -Iseconds) ==="

OUT="runtime/raw_events/shioaji_order_events.regtest.jsonl"
mkdir -p runtime/raw_events
cat > "$OUT" <<JSONL
{"ts":"2026-02-15T00:00:00","kind":"order_cb_v1","payload":{"stat":"Rejected","msg":{"text":"DPBM simulated matched prices exceeded dynamic price banding","qty":1,"upper_limit":31780}}}
{"ts":"2026-02-15T00:00:01","kind":"order_cb_v1","payload":{"stat":"OK","msg":{"text":"accepted"}}}
JSONL

python3 ops/rejects/reject_stats_from_events_v1.py

python3 - <<PY
import json
from pathlib import Path
p = Path("runtime/handoff/state/reject_stats_report_latest.json")
obj = json.loads(p.read_text(encoding="utf-8"))
assert obj["total_events"] >= 1
assert "by_exec_code" in obj
assert "EXEC_TAIFEX_DPBM_REJECT" in obj["by_exec_code"], obj["by_exec_code"]
print("[OK] reject stats regression PASS")
PY

echo "=== [m3 regression reject stats v1] PASS $(date -Iseconds) ==="
