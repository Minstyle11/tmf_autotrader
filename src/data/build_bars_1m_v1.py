#!/usr/bin/env python3
import sqlite3, json
from datetime import datetime

DB_DEFAULT = "runtime/data/tmf_autotrader_v1.sqlite3"

def floor_minute(ts_iso: str) -> str:
    # ts_iso like 2026-01-29T12:10:41.139706 or 2026-01-29T12:10:41.119000
    dt = datetime.fromisoformat(ts_iso)
    dt = dt.replace(second=0, microsecond=0)
    return dt.isoformat(timespec="seconds")

def get_price_and_size(kind: str, payload: dict):
    k = (kind or "").lower()
    # tick_* should have close/price/last_price and volume/size fields.
    # We'll be defensive: try common field names.
    price_keys = ["close", "price", "last_price", "last", "trade_price"]
    size_keys  = ["volume", "qty", "size", "trade_volume", "last_size"]
    px = None
    sz = None
    for kk in price_keys:
        v = payload.get(kk)
        if isinstance(v, (int,float)):
            px = float(v); break
    for kk in size_keys:
        v = payload.get(kk)
        if isinstance(v, (int,float)):
            sz = float(v); break
    return px, sz

def main(db_path: str = DB_DEFAULT):
    con = sqlite3.connect(db_path)
    cur = con.cursor()

    # Ensure bars_1m schema
    cur.execute("""
    CREATE TABLE IF NOT EXISTS bars_1m (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts_min TEXT NOT NULL,
        asset_class TEXT NOT NULL,
        symbol TEXT NOT NULL,
        o REAL NOT NULL,
        h REAL NOT NULL,
        l REAL NOT NULL,
        c REAL NOT NULL,
        v REAL NOT NULL,
        n_trades INTEGER NOT NULL,
        source TEXT NOT NULL,
        UNIQUE(ts_min, asset_class, symbol)
    )
    """)
    con.commit()

    # Pull tick rows (exclude bidask; we only build bars from tick_* for now)
    rows = cur.execute("""
        SELECT ts, asset_class, symbol, kind, payload_json
        FROM norm_ticks
        WHERE kind IN ('tick_fop_v1','tick_stk_v1')
          AND asset_class IN ('FOP','STK')
          AND symbol IS NOT NULL
        ORDER BY ts ASC
    """).fetchall()

    # Aggregate per (ts_min, asset_class, symbol)
    agg = {}  # key -> dict
    skipped = 0
    for ts, asset, sym, kind, pj in rows:
        try:
            payload = json.loads(pj) if pj else {}
        except Exception:
            skipped += 1
            continue

        # prefer payload.datetime if exists, else norm ts
        ts_src = payload.get("datetime") if isinstance(payload, dict) else None
        if isinstance(ts_src, str) and ts_src:
            tmin = floor_minute(ts_src)
        else:
            tmin = floor_minute(ts)

        px, sz = get_price_and_size(kind, payload)
        if px is None:
            skipped += 1
            continue
        if sz is None:
            sz = 0.0

        key = (tmin, asset, sym)
        st = agg.get(key)
        if st is None:
            agg[key] = {
                "o": px, "h": px, "l": px, "c": px,
                "v": float(sz),
                "n": 1,
            }
        else:
            st["h"] = max(st["h"], px)
            st["l"] = min(st["l"], px)
            st["c"] = px
            st["v"] += float(sz)
            st["n"] += 1

    # Upsert bars
    up = 0
    for (tmin, asset, sym), st in agg.items():
        cur.execute("""
            INSERT INTO bars_1m(ts_min, asset_class, symbol, o, h, l, c, v, n_trades, source)
            VALUES(?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(ts_min, asset_class, symbol) DO UPDATE SET
                o=excluded.o,
                h=excluded.h,
                l=excluded.l,
                c=excluded.c,
                v=excluded.v,
                n_trades=excluded.n_trades,
                source=excluded.source
        """, (tmin, asset, sym, st["o"], st["h"], st["l"], st["c"], st["v"], st["n"], "build_bars_1m_v1"))
        up += 1

    con.commit()

    # Report
    print(f"[OK] tick_rows={len(rows)} bars_upserted={up} skipped={skipped}")
    print("=== [BARS COUNT] ===")
    for asset, cnt in cur.execute("SELECT asset_class, COUNT(1) FROM bars_1m GROUP BY asset_class ORDER BY 2 DESC"):
        print(asset, cnt, sep="\t")

    print("\n=== [LATEST 12 bars] ===")
    for r in cur.execute("""
        SELECT ts_min, asset_class, symbol, o,h,l,c,v,n_trades
        FROM bars_1m
        ORDER BY ts_min DESC, asset_class, symbol
        LIMIT 12
    """):
        print("\t".join(map(str, r)))

    con.close()

if __name__ == "__main__":
    main()
