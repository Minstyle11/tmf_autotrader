#!/usr/bin/env python3
"""
Seed a NON-synthetic bidask_fop_v1 event with ts=UTC now (Z) so SystemSafety can pass when reject_synthetic_bidask=1.
"""
import argparse, json, sqlite3
from datetime import datetime, timezone

def utc_ts_z() -> str:
    # millisecond precision + Z
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")

def ingest_ts_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--code", required=True, help="e.g. TMFB6")
    ap.add_argument("--bid", type=float, required=True)
    ap.add_argument("--ask", type=float, required=True)
    ap.add_argument("--bid_vol", type=int, default=1)
    ap.add_argument("--ask_vol", type=int, default=1)
    args = ap.parse_args()

    ts = utc_ts_z()
    ing = ingest_ts_iso()
    payload = {
        "code": args.code,
        "bid": float(args.bid),
        "ask": float(args.ask),
        "bid_price": [float(args.bid)],
        "ask_price": [float(args.ask)],
        "bid_volume": [int(args.bid_vol)],
        "ask_volume": [int(args.ask_vol)],
        "synthetic": False,
    }
    pj = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    sf = "dev_seed_bidask_now_v1"

    con = sqlite3.connect(args.db)
    try:
        cur = con.cursor()
        cur.execute(
            "INSERT INTO events (ts, kind, payload_json, source_file, ingest_ts) VALUES (?, ?, ?, ?, ?)",
            (ts, "bidask_fop_v1", pj, sf, ing),
        )
        con.commit()
        eid = cur.lastrowid
        print(f"[OK] seeded NON-synthetic bidask_fop_v1: event_id={eid} ts={ts} code={args.code} bid={args.bid} ask={args.ask} db={args.db}")
    finally:
        con.close()

if __name__ == "__main__":
    main()
