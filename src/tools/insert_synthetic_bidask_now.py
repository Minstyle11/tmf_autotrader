from __future__ import annotations
import json, os, sqlite3
from datetime import datetime
from pathlib import Path

def insert_now(*, db_path: str, fop_code: str, bid: float, ask: float, source_file: str = "synthetic_insert_now") -> int:
    now = datetime.now().isoformat(timespec="milliseconds")
    payload = {
        "code": str(fop_code),
        "bid": float(bid),
        "ask": float(ask),
        "bid_price": [float(bid)],
        "ask_price": [float(ask)],
        "bid_volume": [10],
        "ask_volume": [10],
        "synthetic": True,
        "source_file": source_file,
        "recv_ts": now,
        "ingest_ts": now,
    }
    con = sqlite3.connect(db_path)
    try:
        con.execute(
            "INSERT INTO events(ts, kind, payload_json, source_file, ingest_ts) VALUES (?,?,?,?,?)",
            (now, "bidask_fop_v1", json.dumps(payload, separators=(",",":")), source_file, now),
        )
        con.commit()
        rid = con.execute("SELECT last_insert_rowid()").fetchone()[0]
        return int(rid)
    finally:
        con.close()

def main() -> int:
    db = os.environ.get("TMF_DB_PATH", "runtime/data/tmf_autotrader_v1.sqlite3")
    fop_code = (os.environ.get("TMF_FOP_CODE", "TMFB6") or "TMFB6").strip()
    bid = float(os.environ.get("TMF_SYNTH_BID", "20000.0"))
    ask = float(os.environ.get("TMF_SYNTH_ASK", "20001.0"))
    Path(db).parent.mkdir(parents=True, exist_ok=True)
    rid = insert_now(db_path=db, fop_code=fop_code, bid=bid, ask=ask)
    now = datetime.now().isoformat(timespec="milliseconds")
    print(f"[OK] insert_synthetic_bidask_now: id={rid} ts~={now} code={fop_code} bid={bid} ask={ask} db={db}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
