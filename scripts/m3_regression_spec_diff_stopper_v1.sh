#!/usr/bin/env bash
set -euo pipefail
DB="${1:-${TMF_DB_PATH:-runtime/data/tmf_autotrader_v1.sqlite3}}"
python3 - "$DB" <<'PY'
import sqlite3, json, sys
from src.execution.spec_diff_stopper_v1 import validate

db = sys.argv[1] if len(sys.argv) > 1 else "runtime/data/tmf_autotrader_v1.sqlite3"
con = sqlite3.connect(db)
try:
    rows = con.execute(
        "SELECT id, ts, payload_json FROM events WHERE kind=? ORDER BY id DESC LIMIT 50",
        ("bidask_fop_v1",),
    ).fetchall()
finally:
    con.close()

bad = 0
for (eid, ts, pjson) in rows:
    try:
        payload = json.loads(pjson) if isinstance(pjson, str) else {}
    except Exception:
        payload = {}
    ok, probs = validate("bidask_fop_v1", payload)
    if not ok:
        bad += 1
        print(f"[FAIL] event_id={eid} ts={ts} problems={probs}")
        # keep printing a few then stop
        if bad >= 5:
            break

if bad == 0:
    print("[OK] spec-diff stopper regression PASS (bidask_fop_v1 schema)")
    raise SystemExit(0)
print(f"[BAD] bad_events={bad}")
raise SystemExit(1)
PY
