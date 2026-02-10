#!/usr/bin/env bash
set -euo pipefail

DB="${1:-${TMF_DB_PATH:-runtime/data/tmf_autotrader_v1.sqlite3}}"

echo "=== [m3 paper-live smoke combo v1] DB=$DB ==="
echo

echo "=== [1] STRICT (TMF_DEV_ALLOW_STALE_BIDASK=0) ==="
TMF_DEV_ALLOW_STALE_BIDASK=0 python3 src/oms/run_paper_live_v1.py --db "$DB"
echo

echo "=== [2] OFFLINE reset cooldown (seconds=0) ==="
python3 - <<'PY' "$DB"
import sys
from src.safety.system_safety_v1 import SystemSafetyEngineV1, SafetyConfigV1
db = sys.argv[1]
s = SystemSafetyEngineV1(db_path=db, cfg=SafetyConfigV1())
s.request_cooldown(seconds=0, code="SMOKE_RESET_COOLDOWN", reason="reset cooldown for offline smoke", details={})
print("[OK] cooldown reset via request_cooldown(seconds=0)")
PY
echo

echo "=== [3] OFFLINE (TMF_DEV_ALLOW_STALE_BIDASK=1) ==="
TMF_DEV_ALLOW_STALE_BIDASK=1 python3 src/oms/run_paper_live_v1.py --db "$DB"
echo

echo "=== [DONE] m3 paper-live smoke combo v1 ==="
