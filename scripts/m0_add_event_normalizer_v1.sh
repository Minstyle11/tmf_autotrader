#!/usr/bin/env bash
set -euo pipefail
PROJ="$HOME/tmf_autotrader"
cd "$PROJ"

mkdir -p src/data scripts

cat > src/data/normalize_events_v1.py <<'PY'
from __future__ import annotations
import json, sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path("runtime/data/tmf_autotrader_v1.sqlite3")

NORMALIZED_SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS norm_ticks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  asset_class TEXT NOT NULL,      -- 'FOP' or 'STK' or 'SYS'
  symbol TEXT,                    -- contract.symbol or stock code
  exchange TEXT,
  kind TEXT NOT NULL,             -- original kind
  payload_json TEXT NOT NULL,
  source_event_id INTEGER,        -- events.id
  ingest_ts TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_norm_ticks_ts ON norm_ticks(ts);
CREATE INDEX IF NOT EXISTS idx_norm_ticks_sym_ts ON norm_ticks(symbol, ts);
"""

def connect(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(str(db_path))
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")
    return con

def classify(kind: str, payload: dict) -> tuple[str, str|None, str|None]:
    # Best-effort: we store raw payload; later we map exact fields once we have real tick samples.
    # For futures/stock the Shioaji payload often contains 'code' or 'symbol' fields.
    k = (kind or "").lower()
    if "fop" in k:
        asset = "FOP"
    elif "stk" in k:
        asset = "STK"
    elif k.startswith("session_"):
        asset = "SYS"
    else:
        asset = "UNK"

    symbol = None
    exchange = None
    for key in ("symbol", "code", "contract", "topic"):
        v = payload.get(key) if isinstance(payload, dict) else None
        if isinstance(v, str) and v:
            if key == "topic":
                # topic may include .../TFE/MXFB6 etc; keep as fallback symbol
                symbol = symbol or v.split("/")[-1]
            else:
                symbol = symbol or v
    for key in ("exchange",):
        v = payload.get(key) if isinstance(payload, dict) else None
        if isinstance(v, str) and v:
            exchange = v
    return asset, symbol, exchange

def normalize_all(db_path: Path) -> int:
    con = connect(db_path)
    try:
        con.executescript(NORMALIZED_SCHEMA)
        rows = con.execute("SELECT id, ts, kind, payload_json, ingest_ts FROM events ORDER BY id").fetchall()
        cur = con.cursor()
        ins = 0
        for eid, ts, kind, payload_json, ingest_ts in rows:
            payload = {}
            try:
                payload = json.loads(payload_json) if payload_json else {}
            except Exception:
                payload = {"_raw": payload_json}
            asset, symbol, exchange = classify(kind, payload)
            cur.execute(
                "INSERT INTO norm_ticks(ts, asset_class, symbol, exchange, kind, payload_json, source_event_id, ingest_ts) VALUES(?,?,?,?,?,?,?,?)",
                (ts, asset, symbol, exchange, kind, json.dumps(payload, ensure_ascii=False), eid, ingest_ts),
            )
            ins += 1
        con.commit()
        return ins
    finally:
        con.close()

def stats(db_path: Path):
    con = connect(db_path)
    try:
        total = con.execute("SELECT COUNT(1) FROM norm_ticks").fetchone()[0]
        by_asset = con.execute("SELECT asset_class, COUNT(1) FROM norm_ticks GROUP BY asset_class ORDER BY 2 DESC").fetchall()
        by_kind = con.execute("SELECT kind, COUNT(1) FROM norm_ticks GROUP BY kind ORDER BY 2 DESC LIMIT 20").fetchall()
        return total, by_asset, by_kind
    finally:
        con.close()

if __name__ == "__main__":
    if not DB_PATH.exists():
        raise SystemExit(f"[FATAL] missing DB: {DB_PATH}")
    n = normalize_all(DB_PATH)
    total, by_asset, by_kind = stats(DB_PATH)
    print(f"[OK] normalized inserted={n}")
    print(f"=== [NORM TOTAL] {total} ===")
    print("=== [BY ASSET] ===")
    for a,c in by_asset:
        print(f"{a}\t{c}")
    print("=== [BY KIND top20] ===")
    for k,c in by_kind:
        print(f"{k}\t{c}")
PY

echo "=== [RUN] normalize events -> norm_ticks ==="
. .venv/bin/activate
python -u src/data/normalize_events_v1.py

if [ -x scripts/pm_tick.sh ]; then
  scripts/pm_tick.sh "M0: added norm_ticks table; normalized events into norm layer (best-effort schema v1)"
fi

echo
echo "=== [DB TABLES] ==="
python3 - <<'PY'
import sqlite3
con=sqlite3.connect("runtime/data/tmf_autotrader_v1.sqlite3")
tabs=[r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()]
print("\n".join(tabs))
con.close()
PY
