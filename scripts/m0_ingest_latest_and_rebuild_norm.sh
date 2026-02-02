#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/tmf_autotrader"

DB="runtime/data/tmf_autotrader_v1.sqlite3"
LATEST="$(ls -1t runtime/data/raw_events_*.jsonl 2>/dev/null | head -n 1 || true)"
if [ -z "$LATEST" ]; then
  echo "[FATAL] no raw_events_*.jsonl found under runtime/data"
  exit 2
fi

echo "=== [LATEST] ==="
echo "$LATEST"
echo

echo "=== [IMPORT] latest jsonl -> DB ==="
. .venv/bin/activate
python -u src/data/store_sqlite_v1.py "$DB" "$LATEST"

echo
echo "=== [REBUILD] norm_ticks (wipe + rebuild from events) ==="
python3 - <<'PY'
import sqlite3, json
db="runtime/data/tmf_autotrader_v1.sqlite3"
con=sqlite3.connect(db)
cur=con.cursor()

# Ensure table exists (schema created by normalize_events_v1.py)
cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='norm_ticks'")
if not cur.fetchone():
    raise SystemExit("[FATAL] norm_ticks table missing. Run normalize script once first.")

cur.execute("DELETE FROM norm_ticks")
con.commit()
print("[OK] wiped norm_ticks")

# Re-run normalization logic (inline; same as classify() best-effort)
def classify(kind: str, payload: dict):
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

    if isinstance(payload, dict):
        # Common Shioaji fields in our now-fixed jsonl
        for key in ("code", "symbol"):
            v = payload.get(key)
            if isinstance(v, str) and v:
                symbol = symbol or v

        # Topic fallback: QUO/v1/FOP/.../TFE/TMFB6 or .../TSE/2330
        topic = payload.get("topic")
        if isinstance(topic, str) and topic:
            symbol = symbol or topic.split("/")[-1]
            parts = topic.split("/")
            if len(parts) >= 2:
                exchange = exchange or parts[-2]

        # explicit exchange
        ex = payload.get("exchange")
        if isinstance(ex, str) and ex:
            exchange = exchange or ex

    return asset, symbol, exchange

rows = cur.execute("SELECT id, ts, kind, payload_json, source_file, ingest_ts FROM events ORDER BY id").fetchall()
ins=0
for eid, ts, kind, pj, src, ingest_ts in rows:
    try:
        payload = json.loads(pj) if pj else {}
    except Exception:
        payload = {"_raw": pj}
    asset, symbol, exchange = classify(kind, payload)
    cur.execute(
        "INSERT INTO norm_ticks(ts, asset_class, symbol, exchange, kind, payload_json, source_event_id, ingest_ts) VALUES(?,?,?,?,?,?,?,?)",
        (ts, asset, symbol, exchange, kind, pj, eid, ingest_ts),
    )
    ins += 1
con.commit()
print("[OK] rebuilt norm_ticks inserted=", ins)

# Quick stats
total = cur.execute("SELECT COUNT(1) FROM norm_ticks").fetchone()[0]
non_sys = cur.execute("SELECT COUNT(1) FROM norm_ticks WHERE asset_class!='SYS'").fetchone()[0]
by_asset = cur.execute("SELECT asset_class, COUNT(1) FROM norm_ticks GROUP BY asset_class ORDER BY 2 DESC").fetchall()
print("=== [NORM TOTAL] ===", total)
print("=== [NORM non_SYS] ===", non_sys)
print("=== [BY ASSET] ===")
for a,c in by_asset:
    print(a, c, sep="\t")

print("\n=== [SAMPLE latest 12 non-SYS] ===")
samp = cur.execute(
    "SELECT e.id, e.ts, e.kind, e.payload_json, n.asset_class, n.symbol "
    "FROM events e JOIN norm_ticks n ON n.source_event_id=e.id "
    "WHERE n.asset_class!='SYS' "
    "ORDER BY e.id DESC LIMIT 12"
).fetchall()
ok_keys=0
for eid, ts, kind, pj, asset, sym in samp:
    try:
        obj=json.loads(pj) if pj else {}
    except Exception:
        obj={}
    keys=list(obj.keys()) if isinstance(obj, dict) else []
    if keys: ok_keys += 1
    code=obj.get("code") if isinstance(obj, dict) else None
    dt=obj.get("datetime") if isinstance(obj, dict) else None
    print(f"id={eid} {asset} sym={sym} kind={kind} code={code} datetime={dt} keys_len={len(keys)}")

print("\n=== [OK] sample_payload_with_keys = %d / %d ===" % (ok_keys, len(samp)))
con.close()
PY

echo
echo "=== [OK] ingest + rebuild done ==="
