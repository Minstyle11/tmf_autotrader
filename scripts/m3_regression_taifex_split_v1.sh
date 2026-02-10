#!/usr/bin/env bash
set -euo pipefail
echo "=== [m3 regression taifex split v1] start $(date -Iseconds) ==="
python3 - <<'PY'
import sqlite3, tempfile
from pathlib import Path

from src.data.store_sqlite_v1 import init_db
from src.oms.paper_oms_v1 import PaperOMS
from src.risk.risk_engine_v1 import RiskEngineV1
from src.safety.system_safety_v1 import SystemSafetyEngineV1, SafetyConfigV1
from src.oms.paper_oms_risk_safety_wrapper_v1 import PaperOMSRiskSafetyWrapperV1

d = Path(tempfile.mkdtemp(prefix="tmf_split_reg_"))
db = d/"tmf.sqlite3"
init_db(db)

# safety: disable bidask requirement for regression determinism
safety = SystemSafetyEngineV1(db_path=str(db), cfg=SafetyConfigV1(require_recent_bidask=0))
risk = RiskEngineV1(db_path=str(db))
oms = PaperOMS(db_path=str(db))
wrap = PaperOMSRiskSafetyWrapperV1(paper_oms=oms, risk=risk, safety=safety, db_path=str(db))

# MARKET qty=12 in DAY should split into 10 + 2 (policy SPLIT)
r = wrap.place_order(
    symbol="TMF", side="BUY", qty=12, order_type="MARKET", price=None,
    meta = {"ref_price": 20000.0, "stop_price": 19950.0, "session_hint": "DAY", "ref_price": 20000.0}
)
assert isinstance(r, dict) and r.get("ok") is True and r.get("status") == "SPLIT_SUBMITTED", r
children = ((r.get("details") or {}).get("children") or (((r.get("exec") or {}).get("details") or {}).get("children")) or [])

# audit-aware: children may include rejected attempts (kept for post-mortem)
ok_orders = [c for c in children if (not isinstance(c, dict))]
rej = [c for c in children if isinstance(c, dict) and c.get("status") == "REJECTED"]

# Expect: risk max_qty_per_order=2 forces adaptation from 10->2, so we should end with 6 accepted orders of qty=2
assert len(ok_orders) >= 6, children
tot_ok_qty = sum(float(getattr(o, "qty", 0.0) or 0.0) for o in ok_orders)
assert abs(tot_ok_qty - 12.0) < 1e-9, tot_ok_qty

# Optional but expected: at least one rejected attempt due to RISK_QTY_LIMIT when initial split tried 10
if rej:
    hit = False
    for x in rej:
        rsk = x.get("risk") if isinstance(x.get("risk"), dict) else {}
        if str(rsk.get("code","")) == "RISK_QTY_LIMIT":
            hit = True
            break
    assert hit, rej

# verify orders persisted (>=6 accepted orders)
con = sqlite3.connect(str(db))
try:
    n = con.execute("SELECT count(1) FROM orders").fetchone()[0]
finally:
    con.close()
assert int(n) >= 6, n

print("[OK] taifex split regression PASS")
PY
echo "=== [m3 regression taifex split v1] PASS $(date -Iseconds) ==="
