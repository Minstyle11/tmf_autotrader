#!/usr/bin/env bash
set -euo pipefail
PROJ="$HOME/tmf_autotrader"
cd "$PROJ"

mkdir -p runtime/data src/data scripts

DB="runtime/data/tmf_autotrader_v1.sqlite3"

cat > src/data/store_sqlite_v1.py <<'PY'
from __future__ import annotations
import json, sqlite3, hashlib, time
from pathlib import Path
from datetime import datetime

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS ingest_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  source_file TEXT NOT NULL UNIQUE,
  sha256 TEXT NOT NULL,
  lines_total INTEGER NOT NULL,
  lines_ok INTEGER NOT NULL,
  lines_bad INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  kind TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  source_file TEXT NOT NULL,
  ingest_ts TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_ts ON events(ts);
CREATE INDEX IF NOT EXISTS idx_events_kind ON events(kind);
CREATE INDEX IF NOT EXISTS idx_events_source ON events(source_file);

-- Placeholders for next milestones (orders/fills/trades/bars)
CREATE TABLE IF NOT EXISTS orders (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  broker_order_id TEXT,
  symbol TEXT,
  side TEXT,
  qty REAL,
  price REAL,
  order_type TEXT,
  status TEXT,
  meta_json TEXT
);

CREATE TABLE IF NOT EXISTS fills (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  broker_order_id TEXT,
  symbol TEXT,
  side TEXT,
  qty REAL,
  price REAL,
  fee REAL,
  tax REAL,
  meta_json TEXT
);

CREATE TABLE IF NOT EXISTS trades (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  open_ts TEXT NOT NULL,
  close_ts TEXT,
  symbol TEXT NOT NULL,
  side TEXT NOT NULL,
  qty REAL NOT NULL,
  entry REAL NOT NULL,
  exit REAL,
  pnl REAL,
  pnl_pct REAL,
  reason_open TEXT,
  reason_close TEXT,
  meta_json TEXT
);

CREATE TABLE IF NOT EXISTS bars_1m (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  symbol TEXT NOT NULL,
  open REAL NOT NULL,
  high REAL NOT NULL,
  low REAL NOT NULL,
  close REAL NOT NULL,
  volume REAL,
  source TEXT,
  meta_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_bars_1m_sym_ts ON bars_1m(symbol, ts);
"""

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path))
    con.execute("PRAGMA journal_mode=WAL;")
    con.execute("PRAGMA synchronous=NORMAL;")
    con.execute("PRAGMA foreign_keys=ON;")
    return con

def init_db(db_path: Path) -> None:
    con = connect(db_path)
    try:
        con.executescript(SCHEMA_SQL)
        con.commit()
    finally:
        con.close()

def already_ingested(con: sqlite3.Connection, source_file: str) -> bool:
    row = con.execute("SELECT 1 FROM ingest_runs WHERE source_file=? LIMIT 1", (source_file,)).fetchone()
    return row is not None

def ingest_jsonl(db_path: Path, jsonl_path: Path) -> None:
    if not jsonl_path.exists():
        raise FileNotFoundError(str(jsonl_path))

    init_db(db_path)
    con = connect(db_path)
    try:
        src = str(jsonl_path.resolve())
        if already_ingested(con, src):
            print(f"[SKIP] already ingested: {src}")
            return

        sh = sha256_file(jsonl_path)
        lines_total = 0
        lines_ok = 0
        lines_bad = 0
        ingest_ts = datetime.now().isoformat(timespec="seconds")

        t0 = time.time()
        cur = con.cursor()
        with jsonl_path.open("r", encoding="utf-8") as f:
            for line in f:
                lines_total += 1
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    ts = str(obj.get("ts", ""))
                    kind = str(obj.get("kind", ""))
                    payload = obj.get("payload", {})
                    cur.execute(
                        "INSERT INTO events(ts, kind, payload_json, source_file, ingest_ts) VALUES(?,?,?,?,?)",
                        (ts, kind, json.dumps(payload, ensure_ascii=False), src, ingest_ts),
                    )
                    lines_ok += 1
                except Exception:
                    lines_bad += 1

        cur.execute(
            "INSERT INTO ingest_runs(ts, source_file, sha256, lines_total, lines_ok, lines_bad) VALUES(?,?,?,?,?,?)",
            (ingest_ts, src, sh, lines_total, lines_ok, lines_bad),
        )
        con.commit()
        dt = time.time() - t0
        print(f"[OK] ingested: {src}")
        print(f"[INFO] sha256={sh}")
        print(f"[INFO] total={lines_total} ok={lines_ok} bad={lines_bad} secs={dt:.2f}")
    finally:
        con.close()

def kind_counts(db_path: Path):
    con = connect(db_path)
    try:
        rows = con.execute(
            "SELECT kind, COUNT(1) AS n FROM events GROUP BY kind ORDER BY n DESC LIMIT 30"
        ).fetchall()
        return rows
    finally:
        con.close()

if __name__ == "__main__":
    import sys
    db = Path(sys.argv[1])
    jl = Path(sys.argv[2])
    ingest_jsonl(db, jl)
    rows = kind_counts(db)
    print("=== [KIND COUNTS top30] ===")
    for k,n in rows:
        print(f"{k}\t{n}")
PY

cat > scripts/import_latest_raw_events_to_db.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/tmf_autotrader"
DB="runtime/data/tmf_autotrader_v1.sqlite3"
LATEST="$(ls -1t runtime/data/raw_events_*.jsonl 2>/dev/null | head -n 1 || true)"
if [ -z "$LATEST" ]; then
  echo "[FATAL] no runtime/data/raw_events_*.jsonl found. Run recorder (MAX_SECONDS=6) first."
  exit 2
fi
echo "[INFO] latest=$LATEST"
. .venv/bin/activate
python -u src/data/store_sqlite_v1.py "$DB" "$LATEST"
echo "=== [OK] DB ready: $DB ==="
SH
chmod +x scripts/import_latest_raw_events_to_db.sh

# run import
bash scripts/import_latest_raw_events_to_db.sh

# update board: keep Data store DOING (already), just tick changelog
if [ -x scripts/pm_tick.sh ]; then
  scripts/pm_tick.sh "M0: SQLite datastore v1 created (WAL); imported latest raw_events into events table"
fi

echo
echo "=== [DB FILE] ==="
ls -la "$DB" || true
