#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Seed a tick_fop_v1 event into TMF AutoTrader sqlite DB (schema v1).

Why:
- Enables deterministic/off-hours paper-live & risk/safety validation
  without depending on real-time Shioaji feed.
- Complements ops_seed_bidask_now_v1.py (bidask is used by staleness guard;
  tick is used by strategy/metrics and future latency/throttle governance).

Table (v1):
  events(id, ts, kind, payload_json, source_file, ingest_ts)
View events_v1 provides source_path alias if present.

Usage:
  python3 scripts/ops_seed_tick_now_v1.py --db runtime/data/tmf_autotrader_v1.sqlite3 \
      --code TMFB6 --price 31775 --qty 1 --source-file "manual_seed_tick"
"""

import argparse
import json
import sqlite3
from datetime import datetime, timezone

def now_ts_iso() -> str:
    # Use UTC Z to avoid naive/local timestamp ambiguity
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')

def utc_ingest_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--db", required=True, help="sqlite3 DB path")
    p.add_argument("--code", required=True, help="FOP code, e.g., TMFB6")
    p.add_argument("--price", type=float, required=True, help="tick price")
    p.add_argument("--qty", type=int, default=1, help="tick quantity (default 1)")
    p.add_argument("--is-buy", type=int, default=1, help="1 buy, 0 sell (default 1)")
    p.add_argument("--ts", default="", help="override event ts (ISO). default now()")
    p.add_argument("--clear-cooldown", type=int, default=0, help="1: clear safety cooldown before seeding (default 0)")
    p.add_argument("--source-file", default="ops_seed_tick_now_v1", help="events.source_file value")
    args = p.parse_args()

    ev_ts = args.ts.strip() or now_ts_iso()
    ingest_ts = utc_ingest_iso()

    # Shioaji-like minimal payload; keep it compact but structured.
    payload = {
        "code": args.code,
        "price": float(args.price),
        "qty": int(args.qty),
        "is_buy": int(args.is_buy),
        # governance flags
        "synthetic": 0,     # keep NON-synthetic by default
        "seed": 1,
        "seed_reason": "offline_deterministic_tick_seed",
    }

    con = sqlite3.connect(args.db)
    try:
        cur = con.cursor()

        # Optional: clear safety cooldown if table exists (best-effort).
        if args.clear_cooldown == 1:
            try:
                cur.execute("UPDATE kv_store SET v = '' WHERE k = 'safety_cooldown_v1'")
            except Exception:
                # Some builds may not have kv_store; ignore.
                pass

        cur.execute(
            "INSERT INTO events(ts, kind, payload_json, source_file, ingest_ts) VALUES(?,?,?,?,?)",
            (ev_ts, "tick_fop_v1", json.dumps(payload, ensure_ascii=False), args.source_file, ingest_ts),
        )
        eid = cur.lastrowid
        con.commit()
        print(f"[OK] seeded tick_fop_v1: event_id={eid} ts={ev_ts} code={args.code} price={args.price} qty={args.qty} source_file={args.source_file}")
    finally:
        con.close()

if __name__ == "__main__":
    main()
