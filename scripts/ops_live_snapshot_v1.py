#!/usr/bin/env python3
import os, json, sqlite3
from pathlib import Path
from datetime import datetime, timezone

DB = os.environ.get("TMF_DB_PATH", "runtime/data/tmf_autotrader_v1.sqlite3")
CODE = os.environ.get("TMF_FOP_CODE", "TMFB6")

EXCLUDE_SOURCE_PREFIXES = ("ops_seed",)  # exclude ops_seed* sources

def connect(db: str):
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    return con

def parse_iso_z(ts: str) -> datetime:
    # "2026-02-10T08:08:39.905Z" -> aware datetime
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts)

def age_seconds(ts: str) -> float:
    now = datetime.now(timezone.utc)
    return (now - parse_iso_z(ts)).total_seconds()

def is_excluded_source(sf: str) -> bool:
    sf = sf or ""
    base = Path(sf).name
    return any(sf.startswith(p) or base.startswith(p) for p in EXCLUDE_SOURCE_PREFIXES)

def latest_event_by_code(con, kind: str, code: str):
    rows = con.execute(
        "SELECT id, ts, payload_json, source_file, ingest_ts FROM events "
        "WHERE kind=? ORDER BY id DESC LIMIT 20000",
        (kind,),
    ).fetchall()
    for r in rows:
        try:
            p = json.loads(r["payload_json"])
        except Exception:
            continue
        if p.get("code") != code:
            continue
        if int(p.get("synthetic", 0) or 0) != 0:
            continue
        if is_excluded_source(str(r["source_file"])):
            continue
        return r, p
    return None, None

def print_header(title: str):
    print("\n" + "=" * 3 + f" {title} " + "=" * 3)

def main():
    print_header("LIVE SNAPSHOT")
    print("generated:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("DB:", DB)
    print("CODE:", CODE)
    print("exclude_source_prefixes:", EXCLUDE_SOURCE_PREFIXES)

    con = connect(DB)

    r_ba, p_ba = latest_event_by_code(con, "bidask_fop_v1", CODE)
    r_tk, p_tk = latest_event_by_code(con, "tick_fop_v1", CODE)

    print_header("LATEST bidask_fop_v1 (non-synth, non-ops_seed)")
    if not r_ba:
        print("[WARN] not found")
    else:
        print("id=", r_ba["id"])
        print("ts=", r_ba["ts"], "age_s=", round(age_seconds(r_ba["ts"]), 3))
        print("source_file=", r_ba["source_file"])
        print("ingest_ts=", r_ba["ingest_ts"])
        for k in ("bid_price", "ask_price", "bid_volume", "ask_volume"):
            v = p_ba.get(k, []) or []
            print(f"{k}_len=", len(v), "head=", v[:5])

    print_header("LATEST tick_fop_v1 (non-synth, non-ops_seed)")
    if not r_tk:
        print("[WARN] not found")
    else:
        print("id=", r_tk["id"])
        print("ts=", r_tk["ts"], "age_s=", round(age_seconds(r_tk["ts"]), 3))
        print("source_file=", r_tk["source_file"])
        print("ingest_ts=", r_tk["ingest_ts"])

    print_header("SystemSafetyEngineV1 check_pre_trade()")
    from src.safety.system_safety_v1 import SystemSafetyEngineV1
    sse = SystemSafetyEngineV1(db_path=DB)
    verdict = sse.check_pre_trade()
    print("ok=", verdict.ok)
    print("code=", verdict.code)
    print("reason=", verdict.reason)
    cfg = (verdict.details or {}).get("cfg", {})
    print("cfg=", json.dumps(cfg, ensure_ascii=False, indent=2))

    print_header("market_metrics_from_db_v1")
    from src.market.market_metrics_from_db_v1 import get_market_metrics_from_db
    mm = get_market_metrics_from_db(db_path=DB, fop_code=CODE)
    print(json.dumps(mm, ensure_ascii=False, indent=2))
    print("non_empty=", bool(mm))

    print_header("DONE")

if __name__ == "__main__":
    main()
