
from __future__ import annotations

import argparse
import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple, List

# v2: build bars_1m from events (tick_*_v1) first; fallback to norm_ticks
# - This removes the dependency that "norm_ticks must be populated".
# - Intended for TMF AutoTrader: Shioaji recorder writes to events table; bars builder consumes events.

def _parse_ts_any(x: Any) -> Optional[datetime]:
    if x is None:
        return None
    if isinstance(x, datetime):
        return x
    s = str(x).strip()
    if not s:
        return None
    # Common formats we saw:
    # - 2026-02-06T13:12:40.538
    # - 2026-02-05T13:09:40.905+08:00
    # - 2022/10/14 09:39:00.354081 (Shioaji doc examples)
    try:
        # ISO8601
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt
    except Exception:
        pass
    for fmt in ("%Y/%m/%d %H:%M:%S.%f", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    return None

def _ts_minute(dt: datetime) -> str:
    # store as ISO-like minute string, keep local naive if naive
    dt2 = dt.replace(second=0, microsecond=0)
    return dt2.isoformat(timespec="minutes")

def _first_float(v: Any) -> Optional[float]:
    if v is None:
        return None
    # list => first element
    if isinstance(v, (list, tuple)) and v:
        return _first_float(v[0])
    # numeric
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if not s:
        return None
    try:
        return float(s)
    except Exception:
        return None

def _pick_price(payload: Dict[str, Any]) -> Optional[float]:
    # Robust across tick schemas
    for k in ("price", "last_price", "deal_price", "trade_price", "close", "last"):
        if k in payload:
            x = _first_float(payload.get(k))
            if x is not None:
                return x
    # Some tick payloads might only have bid/ask; do not use those to fabricate trade ticks
    return None

def _pick_volume(payload: Dict[str, Any]) -> Optional[float]:
    for k in ("volume", "qty", "size", "deal_qty", "trade_volume", "total_volume"):
        if k in payload:
            x = _first_float(payload.get(k))
            if x is not None:
                return x
    return None

def _asset_from_kind(kind: str) -> str:
    k = (kind or "").lower()
    if "fop" in k or "fut" in k or "future" in k:
        return "FOP"
    if "stk" in k or "stock" in k:
        return "STK"
    return "UNK"

def _iter_tick_events(con: sqlite3.Connection, *, since_ymd: Optional[str], kinds: List[str]) -> List[Tuple[str, str, float, float]]:
    """
    Return list of (ts_min, symbol, price, volume) from events payload.
    """
    q = "SELECT ts, kind, payload_json FROM events WHERE kind IN (%s)" % (",".join(["?"] * len(kinds)))
    params: List[Any] = list(kinds)
    if since_ymd:
        # since_ymd like '2026-02-06' -> filter by events.ts prefix best-effort
        q += " AND ts >= ?"
        params.append(since_ymd)
    q += " ORDER BY id ASC"
    out: List[Tuple[str, str, float, float]] = []
    for ts, kind, payload_json in con.execute(q, params):
        try:
            payload = json.loads(payload_json) if payload_json else {}
        except Exception:
            payload = {}
        if not isinstance(payload, dict):
            continue
        sym = (payload.get("code") or payload.get("symbol") or "").strip()
        if not sym:
            continue
        dt = _parse_ts_any(payload.get("datetime") or payload.get("ts") or payload.get("recv_ts") or ts)
        if not dt:
            continue
        px = _pick_price(payload)
        if px is None:
            continue
        vol = _pick_volume(payload)
        if vol is None:
            # allow zero-volume ticks, but keep as 0.0 (better than dropping)
            vol = 0.0
        out.append((_ts_minute(dt), sym, float(px), float(vol)))
    return out

def _ensure_schema(con: sqlite3.Connection) -> None:
    # bars_1m is expected to exist from init_db; but keep it safe
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS bars_1m (
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
        """
    )
    con.commit()

def build_bars_1m_from_events(*, db_path: str, since_ymd: Optional[str], kinds: List[str], dry: bool = False) -> Dict[str, Any]:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        _ensure_schema(con)
        ticks = _iter_tick_events(con, since_ymd=since_ymd, kinds=kinds)
        if not ticks:
            return {"ok": True, "tick_rows": 0, "bars_upserted": 0, "skipped": 0, "note": "no tick events matched (events->ticks empty)"}

        # aggregate to 1m bars
        agg: Dict[Tuple[str, str], Dict[str, Any]] = {}
        skipped = 0
        for ts_min, sym, px, vol in ticks:
            key = (ts_min, sym)
            b = agg.get(key)
            if b is None:
                b = {"o": px, "h": px, "l": px, "c": px, "v": float(vol), "n": 1}
                agg[key] = b
            else:
                b["h"] = max(b["h"], px)
                b["l"] = min(b["l"], px)
                b["c"] = px
                b["v"] += float(vol)
                b["n"] += 1

        if dry:
            return {"ok": True, "tick_rows": len(ticks), "bars_upserted": len(agg), "skipped": skipped, "dry": True}

        up = 0
        for (ts_min, sym), b in agg.items():
            asset = _asset_from_kind("fop" if sym.endswith(("B6","R1")) else "stk")  # heuristic; kind info not kept per tick row
            con.execute(
                """
                INSERT INTO bars_1m (ts_min, asset_class, symbol, o, h, l, c, v, n_trades, source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(ts_min, asset_class, symbol) DO UPDATE SET
                    asset_class=excluded.asset_class,
                    o=excluded.o, h=excluded.h, l=excluded.l, c=excluded.c,
                    v=excluded.v, n_trades=excluded.n_trades,
                    source=excluded.source
                """,
                (ts_min, asset, sym, b["o"], b["h"], b["l"], b["c"], b["v"], int(b["n"]), "build_bars_1m_v1.events_v2"),
            )
            up += 1
        con.commit()
        return {"ok": True, "tick_rows": len(ticks), "bars_upserted": up, "skipped": skipped}
    finally:
        con.close()

def main() -> int:
    p = argparse.ArgumentParser(description="build bars_1m from TMF sqlite db (v2: events-first)")
    p.add_argument("--db", default="runtime/data/tmf_autotrader_v1.sqlite3")
    p.add_argument("--since", default="", help="YYYY-MM-DD (optional; filters events.ts >= since)")
    p.add_argument("--kinds", default="tick_fop_v1,tick_stk_v1", help="comma-separated event kinds to treat as ticks")
    p.add_argument("--dry", action="store_true")
    args = p.parse_args()

    since = (args.since or "").strip() or None
    kinds = [x.strip() for x in (args.kinds or "").split(",") if x.strip()]
    if not kinds:
        kinds = ["tick_fop_v1", "tick_stk_v1"]

    r = build_bars_1m_from_events(db_path=str(args.db), since_ymd=since, kinds=kinds, dry=bool(args.dry))
    print(json.dumps(r, ensure_ascii=False, indent=2))
    return 0 if r.get("ok") else 1

if __name__ == "__main__":
    raise SystemExit(main())
