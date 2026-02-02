#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/tmf_autotrader"

python3 - <<'PY'
import sqlite3, json, textwrap

DB="runtime/data/tmf_autotrader_v1.sqlite3"
con=sqlite3.connect(DB)

def show(kind):
    row = con.execute(
        "SELECT id, ts, kind, payload_json FROM events WHERE kind=? ORDER BY id DESC LIMIT 1",
        (kind,)
    ).fetchone()
    if not row:
        print(f"=== {kind} ===\n[MISS]\n")
        return
    eid, ts, k, pj = row
    payload = json.loads(pj) if pj else {}
    keys = sorted(list(payload.keys())) if isinstance(payload, dict) else []
    print(f"=== {kind} (event_id={eid} ts={ts}) ===")
    print("[KEYS]", keys)
    # Print a compact view of payload (avoid huge spam)
    s = json.dumps(payload, ensure_ascii=False, indent=2)
    if len(s) > 4000:
        print(s[:4000] + "\n... (truncated) ...")
    else:
        print(s)
    print()

for k in ["tick_fop_v1", "bidask_fop_v1", "tick_stk_v1", "bidask_stk_v1"]:
    show(k)

con.close()
PY
