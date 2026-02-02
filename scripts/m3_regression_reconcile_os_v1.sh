#!/bin/bash
set -euo pipefail
cd "$HOME/tmf_autotrader"
echo "=== [m3 regression reconcile os v1] start $(date -Iseconds) ==="

python3 - <<'PY'
import os
import sqlite3
import tempfile
from pathlib import Path
from datetime import datetime

from src.oms.paper_oms_v1 import PaperOMS
from src.data.store_sqlite_v1 import init_db
from ops.reconcile.reconcile_engine import reconcile_db

def _cols(con, table):
    return [r[1] for r in con.execute(f"PRAGMA table_info({table})").fetchall()]

def _required_cols(con, table):
    # columns that are NOT NULL and have no default and are not INTEGER PRIMARY KEY
    req = []
    for cid, name, ctype, notnull, dflt, pk in con.execute(f"PRAGMA table_info({table})").fetchall():
        if int(pk) == 1:
            continue
        if int(notnull) == 1 and dflt is None:
            req.append((str(name), str(ctype or "")))
    return req
def _insert_orphan_fill(db_path):
    con = sqlite3.connect(db_path)
    try:
        if "fills" not in [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]:
            return False, "no fills table"
        cols = _cols(con, "fills")

        # choose FK-ish column name
        fk_col = None
        if "order_id" in cols:
            fk_col = "order_id"
        elif "broker_order_id" in cols:
            fk_col = "broker_order_id"
        else:
            return False, "fills has no order_id/broker_order_id col"

        req = _required_cols(con, "fills")

        # craft a minimal row for required cols
        row = {}
        if fk_col == "order_id":
            row["order_id"] = 999999999  # orphan
        else:
            row["broker_order_id"] = "ORPHAN_BROKER_ORDER_ID_999999999"

        now = datetime.now().isoformat(timespec="seconds")
        for name, ctype in req:
            if name in row:
                continue
            n = name.lower()
            if "ts" in n or "time" in n:
                row[name] = now
            elif "symbol" in n:
                row[name] = "TMF"
            elif "side" in n:
                row[name] = "BUY"
            elif "qty" in n or "volume" in n:
                row[name] = 1.0
            elif "price" in n:
                row[name] = 20000.0
            elif "json" in n or "payload" in n or "meta" in n:
                row[name] = "{}"
            elif "fee" in n or "commission" in n:
                row[name] = 0.0
            elif "tax" in n:
                row[name] = 0.0
            else:
                if "int" in ctype.lower():
                    row[name] = 0
                elif "real" in ctype.lower() or "float" in ctype.lower() or "num" in ctype.lower():
                    row[name] = 0.0
                else:
                    row[name] = ""

        # ensure only existing cols
        row = {k: v for k, v in row.items() if k in cols}

        keys = list(row.keys())
        vals = [row[k] for k in keys]
        q = ",".join(["?"] * len(keys))
        sql = f"INSERT INTO fills({','.join(keys)}) VALUES({q})"
        con.execute(sql, vals)
        con.commit()
        return True, f"inserted orphan fill via {fk_col}"
    finally:
        con.close()

# temp db
tmpdir = tempfile.mkdtemp(prefix="tmf_autotrader_recon_regtest_")
db = Path(tmpdir) / "recon.sqlite3"

init_db(db)

oms = PaperOMS(db)
# place+match one good order (creates orders/fills/trades per PaperOMS behavior)
o = oms.place_order(symbol="TMF", side="BUY", qty=1.0, order_type="MARKET", price=None, meta={"stop_price": 19950.0})
oms.match(o, market_price=20000.5, liquidity_qty=10.0, reason="recon_regtest_fill")

r1 = reconcile_db(str(db))
print("[CASE] good_db ->", r1.code, "ok=", r1.ok)
assert r1.ok, f"expected OK; got {r1}"

ok, msg = _insert_orphan_fill(str(db))
print("[INFO] orphan_fill_insert ->", ok, msg)

r2 = reconcile_db(str(db))
print("[CASE] orphan_fill_db ->", r2.code, "ok=", r2.ok)
if ok:
    assert (not r2.ok) and r2.code in ("RECON_ORPHAN_FILLS", "RECON_FILLED_WITHOUT_FILLS", "RECON_MISSING_TABLES", "RECON_ORPHAN_TRADES"), r2

print("[OK] m3 reconcile regression PASS (temp db):", db)
PY

echo "=== [m3 regression reconcile os v1] PASS $(date -Iseconds) ==="
