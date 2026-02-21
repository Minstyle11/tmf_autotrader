#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

OUT_JSON="${TMF_CHAOS_DRILL_OUT_JSON:-runtime/logs/chaos_drill_v1.latest.json}"
OUT_LOG="${TMF_CHAOS_DRILL_OUT_LOG:-runtime/logs/chaos_drill_v1.latest.log}"

python3 -m py_compile src/ops/chaos/chaos_drill_v1.py src/ops/latency/latency_budget.py src/ops/latency/backpressure_governor.py src/safety/system_safety_v1.py

python3 -c "from src.ops.chaos.chaos_drill_v1 import main; main()"

echo "[OK] chaos drill PASS"
echo "[ARTIFACT] $OUT_JSON"
echo "[ARTIFACT] $OUT_LOG"
