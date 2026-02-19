#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

TS="$(date +%Y%m%d_%H%M%S)"
LOG="runtime/logs/paper_live_integration_smoke_v1.${TS}.log"
LAST="runtime/logs/paper_live_integration_smoke_v1.last.log"
: > "$LOG"

echo "=== [paper-live integration smoke v1] start $(date -Iseconds) ===" | tee -a "$LOG"

TMPD="$(mktemp -d -t tmf_paper_live_smoke.XXXXXX)"
DB="$TMPD/tmf_autotrader_smoke.sqlite3"
echo "[INFO] smoke tmpdb: $DB" | tee -a "$LOG"
echo "[INFO] tmpdb kept at: $DB" | tee -a "$LOG"

# --- SMOKE OVERRIDES (regression-only; do NOT affect production) ---
export TMF_HALT_DATES_CSV=""
export TMF_REQUIRE_SESSION_OPEN="0"
export TMF_IGNORE_MARKET_CALENDAR="1"
echo "[INFO] smoke override: TMF_HALT_DATES_CSV=\"\" (ignore holidays for regression)" | tee -a "$LOG"
echo "[INFO] smoke override: TMF_REQUIRE_SESSION_OPEN=0 (ignore session closed for regression)" | tee -a "$LOG"
echo "[INFO] smoke override: TMF_IGNORE_MARKET_CALENDAR=1 (bypass market calendar for regression)" | tee -a "$LOG"
# --- /SMOKE OVERRIDES ---

# 0) init fresh db (no production pollution)
python3 - "$DB" <<'PY_INIT' 2>&1 | tee -a "$LOG"
from pathlib import Path
from src.data.store_sqlite_v1 import init_db
db = Path(__import__("sys").argv[1])
db.parent.mkdir(parents=True, exist_ok=True)
init_db(db)
print("[OK] init_db:", db)
PY_INIT

# --- SEED_SYNTHETIC_BIDASK_FOR_SMOKE_V1 ---
# Purpose: make smoke deterministic even when live recorder is not running.
# This is TEST-ONLY. Production still relies on Shioaji order/deal/bidask events.
python3 - "$DB" <<'PY_SEED' 2>&1 | tee -a "$LOG"
import json, sqlite3
from datetime import datetime, timezone
from pathlib import Path

db_path = Path(__import__("sys").argv[1])
con = sqlite3.connect(str(db_path))
try:
    cols = con.execute("PRAGMA table_info(events)").fetchall()
    required = []
    for cid, name, typ, notnull, dflt, pk in cols:
        name = str(name)
        typ = (str(typ) if typ is not None else "").upper()
        if name in ("ts", "kind", "payload_json"):
            continue
        if int(notnull or 0) == 1 and dflt is None and int(pk or 0) == 0:
            required.append((name, typ))

    ts = datetime.now(timezone.utc).astimezone().isoformat(timespec="milliseconds")
    payload = {
        "code": "TMFB6",
        "bid_price": [20000.0, 19999.0, 19998.0, 19997.0, 19996.0],
        "ask_price": [20001.0, 20002.0, 20003.0, 20004.0, 20005.0],
        "bid_volume": [10, 9, 8, 7, 6],
        "ask_volume": [10, 9, 8, 7, 6],
        "synthetic": False,
        "note": "smoke-only seed",
    }

    fields = ["ts", "kind", "payload_json"]
    values = [ts, "bidask_fop_v1", json.dumps(payload, ensure_ascii=False)]

    def _default_for(name: str, typ: str):
        n = name.lower()
        if n in ("source_file", "source"):
            return "SMOKE_SYNTHETIC"
        if "INGEST" in n and ("TS" in n or "TIME" in n):
            return ts
        if "INT" in typ:
            return 0
        if "REAL" in typ or "FLOA" in typ or "DOUB" in typ:
            return 0.0
        return "SMOKE_SYNTHETIC"

    for name, typ in required:
        fields.append(name)
        values.append(_default_for(name, typ))

    placeholders = ",".join(["?"] * len(fields))
    sql = "INSERT INTO events(%s) VALUES (%s)" % (",".join(fields), placeholders)
    con.execute(sql, tuple(values))
    con.commit()
    print("[OK] seeded NON-synthetic bidask_fop_v1 for TMFB6 ts=", ts, "extra_required=", [n for n,_ in required])
finally:
    con.close()
PY_SEED
# --- /SEED_SYNTHETIC_BIDASK_FOR_SMOKE_V1 ---

# 1) runner must compile + run (point to tmpdb)
python3 -m py_compile src/oms/run_paper_live_v1.py 2>&1 | tee -a "$LOG"
# --- AUTO-SEED LIVE BIDASK NOW (smoke hardening) ---
# Ensure live DB has a FRESH non-synthetic bidask right before paper-live,
# and clear cooldown so stale from previous run doesn't cascade.
SEED_DB="runtime/data/tmf_autotrader_v1.sqlite3"
SEED_CODE="${TMF_FOP_CODE:-TMFB6}"
SEED_BID="${TMF_SEED_BID:-31774}"
SEED_ASK="${TMF_SEED_ASK:-31775}"
python3 scripts/ops_seed_bidask_now_v1.py --db "$SEED_DB" --code "$SEED_CODE" --bid "$SEED_BID" --ask "$SEED_ASK" --clear-cooldown=1
# --- END AUTO-SEED ---

python3 src/oms/run_paper_live_v1.py --db "$DB" 2>&1 | tee -a "$LOG"

# 2) DB assertions: must have (a) at least one FILLED order, (b) at least one REJECTED with meta_json.risk_verdict.code
python3 - "$DB" <<'PY_ASSERT' 2>&1 | tee -a "$LOG"
from __future__ import annotations
import json, sqlite3
from pathlib import Path

db = Path(__import__("sys").argv[1])
assert db.exists(), f"missing db: {db}"

con = sqlite3.connect(str(db))
con.row_factory = sqlite3.Row
try:
    filled = con.execute("SELECT COUNT(*) AS c FROM orders WHERE status='FILLED'").fetchone()["c"]
    assert int(filled) >= 1, f"expected >=1 FILLED order, got {filled}"

    rows = con.execute(
        "SELECT id, ts, broker_order_id, meta_json FROM orders WHERE status='REJECTED' ORDER BY id DESC LIMIT 50"
    ).fetchall()

    ok = False
    last = None
    for r in rows:
        last = r
        mj = r["meta_json"]
        if not mj:
            continue
        try:
            j = json.loads(mj)
        except Exception:
            continue
        rv = j.get("risk_verdict")
        if isinstance(rv, dict) and isinstance(rv.get("code"), str) and rv.get("code"):
            ok = True
            break

    assert ok, "expected at least one REJECTED order with meta_json.risk_verdict.code"
    print("[PASS] db assertions ok")
    if last is not None:
        print("[INFO] last_rejected_id=", last["id"])
finally:
    con.close()
PY_ASSERT

echo "=== [paper-live integration smoke v1] PASS $(date -Iseconds) ===" | tee -a "$LOG"
cp -f "$LOG" "$LAST"
echo "[OK] wrote log: $LAST"
echo "[INFO] tmpdb kept at: $DB"
