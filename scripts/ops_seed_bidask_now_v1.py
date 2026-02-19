from __future__ import annotations
import argparse, json, sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

def _now_ms() -> str:
    # UTC ISO w/ ms precision, trailing 'Z'
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z').replace("+00:00", "Z")
def _set_cooldown(con: sqlite3.Connection, value: Dict[str, Any]) -> None:
    con.execute(
        "CREATE TABLE IF NOT EXISTS safety_state("
        "key TEXT PRIMARY KEY,"
        "value_json TEXT,"
        "ts TEXT"
        ")"
    )
    con.execute(
        "INSERT INTO safety_state(key, value_json, ts) VALUES(?,?,?) "
        "ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, ts=excluded.ts",
        ("cooldown", json.dumps(value, ensure_ascii=False), datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")),
    )

def _clear_cooldown(con: sqlite3.Connection) -> None:
    _set_cooldown(con, {"until_epoch": 0})

def _latest_bar_close(con: sqlite3.Connection, asset_class: str, symbol: str) -> Optional[float]:
    row = con.execute(
        "SELECT c FROM bars_1m WHERE asset_class=? AND symbol=? ORDER BY ts_min DESC LIMIT 1",
        (str(asset_class), str(symbol)),
    ).fetchone()
    if not row:
        return None
    try:
        return float(row[0])
    except Exception:
        return None

def _insert_bidask_event(
    con: sqlite3.Connection,
    *,
    code: str,
    bid: float,
    ask: float,
    bid_vol: int,
    ask_vol: int,
    synthetic: bool,
    source_file: str,
    ingest_ts: str,
    recv_ts: str,
    ts: Optional[str] = None,
) -> int:
    # Match recorder shape: bid_price/ask_price/bid_volume/ask_volume are LISTs (L1..L5 book)
    payload = {
        "code": str(code),
        "bid_price": [float(bid)],
        "ask_price": [float(ask)],
        "bid_volume": [int(bid_vol)],
        "ask_volume": [int(ask_vol)],
        # keep scalar convenience too (harmless if extra keys)
        "bid": float(bid),
        "ask": float(ask),
        "source_file": str(source_file),
        "ingest_ts": str(ingest_ts),
        "recv_ts": str(recv_ts),
        "synthetic": bool(synthetic),
    }
    ts = ts or _now_ms()
    con.execute(
        "INSERT INTO events(kind, ts, payload_json, source_file, ingest_ts) VALUES(?,?,?,?,?)",
        ("bidask_fop_v1", ts, json.dumps(payload, ensure_ascii=False), str(source_file), str(ingest_ts)),
    )
    return int(con.execute("SELECT last_insert_rowid()").fetchone()[0])

def main():
    p = argparse.ArgumentParser(description="Seed NON-synthetic bidask_fop_v1 event into DB + optional clear cooldown (v2, list-shaped payload)")
    p.add_argument("--db", default="runtime/data/tmf_autotrader_v1.sqlite3", help="sqlite db path")
    p.add_argument("--code", default="TMFB6", help="fop_code, e.g. TMFB6")
    p.add_argument("--bid", type=float, default=None, help="bid price (optional; if omitted, use --from-bars)")
    p.add_argument("--ask", type=float, default=None, help="ask price (optional; if omitted, use --from-bars + --spread)")
    p.add_argument("--bid-vol", type=int, default=1, help="bid volume for seed (default 1)")
    p.add_argument("--ask-vol", type=int, default=1, help="ask volume for seed (default 1)")
    p.add_argument("--from-bars", type=int, default=1, help="1: derive from latest bars_1m close when bid/ask missing")
    p.add_argument("--bars-symbol", default="", help="bars symbol for close lookup; default=code")
    p.add_argument("--spread", type=float, default=1.0, help="ask = bid + spread when deriving from bars")
    p.add_argument("--asset-class", default="FOP", help="bars_1m asset_class for deriving close (default FOP)")
    p.add_argument("--clear-cooldown", type=int, default=1, help="1: clear safety cooldown before seeding")
    p.add_argument("--source-file", default="ops_seed_bidask_now_v1", help="events.source_file value")
    args = p.parse_args()

    db = Path(args.db)
    con = sqlite3.connect(str(db))
    try:
        con.execute("PRAGMA foreign_keys=ON")
        if args.clear_cooldown == 1:
            _clear_cooldown(con)

        bid = args.bid
        ask = args.ask
        if (bid is None or ask is None) and args.from_bars == 1:
            bars_sym = (args.bars_symbol or "").strip() or str(args.code)
            c = _latest_bar_close(con, str(args.asset_class), bars_sym)
            if c is None:
                raise SystemExit(f"[FAIL] cannot derive from bars_1m: missing latest close for asset_class={args.asset_class} symbol={bars_sym}")
            bid = float(c) if bid is None else float(bid)
            ask = float(bid + float(args.spread)) if ask is None else float(ask)

        if bid is None or ask is None:
            raise SystemExit("[FAIL] bid/ask missing; provide --bid/--ask or enable --from-bars=1")

        ts = _now_ms()
        ingest_ts = ts
        recv_ts = ts
        eid = _insert_bidask_event(
            con,
            code=str(args.code),
            bid=float(bid),
            ask=float(ask),
            bid_vol=int(args.bid_vol),
            ask_vol=int(args.ask_vol),
            synthetic=False,
            source_file=str(args.source_file),
            ingest_ts=str(ingest_ts),
            recv_ts=str(recv_ts),
            ts=str(ts),
        )
        con.commit()
        print(f"[OK] seeded live bidask (list-shaped): event_id={eid} ts={ts} code={args.code} bid={bid} ask={ask} clear_cooldown={args.clear_cooldown}")
    finally:
        con.close()

if __name__ == "__main__":
    main()
