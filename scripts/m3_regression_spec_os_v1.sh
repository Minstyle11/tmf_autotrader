#!/bin/bash
set -euo pipefail
cd "$HOME/tmf_autotrader"
echo "=== [m3 regression spec os v1] start $(date -Iseconds) ==="

python3 -m py_compile spec/spec_updater.py spec/spec_diff_stopper.py

# 1) should PASS when same
python3 spec/spec_updater.py --mode check --report snapshots/spec_diff/spec_diff_report_latest.md

# 2) make a deliberate diff -> should EXIT 2
tmp=runtime/spec/taifex_spec_latest_tmp.json
python3 - <<'PY'
import json
from pathlib import Path
p = Path("runtime/spec/taifex_spec_latest.json")
obj = json.loads(p.read_text(encoding="utf-8"))
obj.setdefault("products", {}).setdefault("TXF", {})["market_order_limit_regular"] = 10
Path("runtime/spec/taifex_spec_latest_tmp.json").write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
PY

set +e
python3 spec/spec_updater.py --candidate "$tmp" --mode check --report snapshots/spec_diff/spec_diff_report_diff.md
rc=$?
set -e
if [ "$rc" -ne 2 ]; then
  echo "[FAIL] expected exit=2 when diff; got rc=$rc"
  exit 1
fi
echo "[PASS] diff stopper exit code OK (rc=2)"

echo "=== [m3 regression spec os v1] PASS $(date -Iseconds) ==="
