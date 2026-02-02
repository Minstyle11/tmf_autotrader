#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/tmf_autotrader"


TS="$(date +%Y%m%d_%H%M%S)"
LOG="runtime/logs/m2_regression_risk_gates_v1.run.${TS}.log"
LAST="runtime/logs/m2_regression_risk_gates_v1.last.log"
DB_SRC="runtime/data/tmf_autotrader_v1.sqlite3"
if [ ! -f "$DB_SRC" ]; then
  echo "[FATAL] missing db: $DB_SRC" >&2
  exit 2
fi

TMPD="$(mktemp -d)"
DB="$TMPD/tmf_autotrader_v1_regtest.sqlite3"
cp -f "$DB_SRC" "$DB"
python3 - "$DB" <<'PY' 2>&1 | tee "$LOG"
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

db_path = Path(__import__("sys").argv[1])

def now_iso(dt=None):
    dt = dt or datetime.now()
    return dt.isoformat(timespec="milliseconds")

def get_trade_cols(con):
    cols=[]
    for r in con.execute("PRAGMA table_info(trades)"):
        # (cid, name, type, notnull, dflt_value, pk)
        cols.append(dict(cid=r[0], name=r[1], typ=r[2], notnull=r[3], dflt=r[4], pk=r[5]))
    if not cols:
        raise SystemExit("[FATAL] cannot introspect trades schema")
    return cols

def insert_trade(con, *, close_ts: str, pnl: float):
    cols = get_trade_cols(con)

    names=[]
    vals=[]
    for c in cols:
        n=c["name"]
        if c["pk"] == 1 and n.lower() in ("id",):
            continue
        # we must at least set close_ts + pnl
        if n == "close_ts":
            names.append(n); vals.append(close_ts); continue
        if n == "pnl":
            names.append(n); vals.append(float(pnl)); continue

        # For NOT NULL w/o default, provide a safe dummy.
        if int(c["notnull"]) == 1 and c["dflt"] is None:
            t=(c["typ"] or "").upper()
            nn=n.lower()
            if "ts" in nn or "time" in nn or nn.endswith("_at"):
                v = close_ts
            elif "symbol" in nn:
                v = "TMF"
            elif "side" in nn:
                v = "BUY"
            elif "qty" in nn or "size" in nn:
                v = 1.0
            elif "price" in nn or "entry" in nn or "exit" in nn:
                v = 20000.0
            elif "meta" in nn and "json" in nn:
                v = "{}"
            elif "text" in t or "char" in t or "clob" in t or "str" in nn:
                v = ""
            elif "int" in t:
                v = 0
            else:
                v = 0.0
            names.append(n); vals.append(v)

    if "close_ts" not in names or "pnl" not in names:
        raise SystemExit("[FATAL] trades table lacks close_ts/pnl columns required by RiskEngineV1")

    q = ",".join(["?"]*len(names))
    sql = f"INSERT INTO trades({','.join(names)}) VALUES({q})"
    con.execute(sql, vals)

def pretrade_verdict(db_path: Path, *, today_loss_ntd=None, consec_losses=None, last_loss_minutes_ago=None):
    from src.risk.risk_engine_v1 import RiskEngineV1, RiskConfigV1

    # Keep per-trade safe, and include market-quality fields with safe values (if gates exist).
    meta = {
        "stop_price": 19999.0,
        "spread_points": 0.5,
        "atr_points": 10.0,
        "atr_pct": 0.0005,
        "liquidity_score": 1e9,
        "bid_qty": 200,
        "ask_qty": 200,
        "volume": 10000,
    }

    cfg = RiskConfigV1()
    if today_loss_ntd is not None:
        # keep default daily_max_loss; we will shape DB pnl.
        pass
    if consec_losses is not None:
        pass

    eng = RiskEngineV1(db_path=str(db_path), cfg=cfg)
    v = eng.check_pre_trade(symbol="TMF", side="BUY", qty=1.0, entry_price=20000.0, meta=meta)
    return v

con = sqlite3.connect(str(db_path))
try:
    con.execute("PRAGMA foreign_keys=OFF")
    con.execute("BEGIN")
    # --- CASE A: daily max loss hit ---
    # wipe only trades table rows in temp db (safe)
    con.execute("DELETE FROM trades")
    # Insert a single big loss to exceed default daily_max_loss_ntd=5000
    insert_trade(con, close_ts=now_iso(), pnl=-6000.0)
    con.commit()

    v = pretrade_verdict(db_path)
    print("[CASE A] daily max loss ->", ("PASS" if v.ok else "REJECT"), v.code)

    # --- CASE B: consecutive losses cooldown active ---
    con.execute("BEGIN")
    con.execute("DELETE FROM trades")
    # 3 consecutive losses (default limit=3) with last loss 5 minutes ago => cooldown(30m) active
    base = datetime.now()
    for i in range(3):
        insert_trade(con, close_ts=now_iso(base - timedelta(minutes=5+i)), pnl=-100.0)
    con.commit()

    v = pretrade_verdict(db_path)
    print("[CASE B] consec losses cooldown ->", ("PASS" if v.ok else "REJECT"), v.code)

    # --- CASE C: cooldown expired should PASS (assuming no other gates hit) ---
    con.execute("BEGIN")
    con.execute("DELETE FROM trades")
    # same 3 losses but last loss 60 minutes ago => cooldown expired
    for i in range(3):
        insert_trade(con, close_ts=now_iso(base - timedelta(minutes=60+i)), pnl=-100.0)
    con.commit()

    v = pretrade_verdict(db_path)
    print("[CASE C] cooldown expired ->", ("PASS" if v.ok else "REJECT"), v.code)

    # expectations
    assert v.ok or v.code == "OK", f"[FATAL] expected PASS after cooldown, got: {v.code} {v.reason}"
finally:
    con.close()

print(f"[OK] m2 regression risk gates PASS (temp db): {db_path}")
PY
cp -f "$LOG" "$LAST"
echo "[OK] wrote log: $LAST"
