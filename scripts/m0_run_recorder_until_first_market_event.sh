#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/tmf_autotrader"

echo "=== [INFO] This will run recorder up to 120s and stop automatically. ==="
echo "=== [INFO] Goal: capture at least 1 non-SYS event (FOP/STK tick or bidask). ==="

. .venv/bin/activate

# Run recorder with a longer max window to catch any pre-open/market data; file will always exist.
MAX_SECONDS=120 python -u src/broker/shioaji_recorder.py || true

echo
echo "=== [LOCATE] latest raw_events_*.jsonl ==="
LATEST="$(ls -1t runtime/data/raw_events_*.jsonl 2>/dev/null | head -n 1 || true)"
if [ -z "$LATEST" ]; then
  echo "[FATAL] no raw_events file found"
  exit 2
fi
echo "[OK] latest=$LATEST"

echo
echo "=== [IMPORT] latest into DB ==="
python -u src/data/store_sqlite_v1.py "runtime/data/tmf_autotrader_v1.sqlite3" "$LATEST"

echo
echo "=== [NORMALIZE] rebuild norm_ticks from events (append) ==="
python -u src/data/normalize_events_v1.py

echo
echo "=== [CHECK] non-SYS events in norm_ticks ==="
python3 - <<'PY'
import sqlite3
con=sqlite3.connect("runtime/data/tmf_autotrader_v1.sqlite3")
total=con.execute("SELECT COUNT(1) FROM norm_ticks").fetchone()[0]
non_sys=con.execute("SELECT COUNT(1) FROM norm_ticks WHERE asset_class!='SYS'").fetchone()[0]
by_asset=con.execute("SELECT asset_class, COUNT(1) FROM norm_ticks GROUP BY asset_class ORDER BY 2 DESC").fetchall()
print("[INFO] norm_total =", total)
print("[INFO] non_SYS =", non_sys)
print("=== [BY ASSET] ===")
for a,c in by_asset:
    print(a, c, sep="\t")
if non_sys>0:
    print("=== [SAMPLE non-SYS last 5] ===")
    rows=con.execute("SELECT ts, asset_class, symbol, kind FROM norm_ticks WHERE asset_class!='SYS' ORDER BY id DESC LIMIT 5").fetchall()
    for r in rows:
        print("\t".join([str(x) for x in r]))
else:
    print("[WARN] still no market events captured (likely before market open).")
con.close()
PY

echo
echo "=== [OK] run complete ==="
