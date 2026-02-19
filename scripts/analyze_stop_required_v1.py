#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyze RISK_STOP_REQUIRED rejections from orders table.
Outputs:
  - runtime/reports/stop_required_audit_latest.json
  - runtime/reports/stop_required_audit_latest.md
  - sha256 sidecars
"""
from __future__ import annotations
import json, sqlite3, hashlib
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter, defaultdict

DB = Path("runtime/data/tmf_autotrader_v1.sqlite3")
OUTDIR = Path("runtime/reports")
OUT_JSON = OUTDIR / "stop_required_audit_latest.json"
OUT_MD   = OUTDIR / "stop_required_audit_latest.md"

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def write_sha256_sidecar(p: Path) -> None:
    dig = sha256_file(p)
    p.with_suffix(p.suffix + ".sha256.txt").write_text(f"{dig}  {p.name}\n", encoding="utf-8")

def safe_json_loads(s: str | None) -> dict:
    if not s:
        return {}
    try:
        x = json.loads(s)
        return x if isinstance(x, dict) else {"_non_dict_meta": True, "value": x}
    except Exception as e:
        return {"_meta_parse_error": f"{type(e).__name__}: {e}", "_raw": s[:500]}

def main() -> None:
    if not DB.exists():
        raise SystemExit(f"[FATAL] missing DB: {DB}")

    OUTDIR.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB))
    con.row_factory = sqlite3.Row
    try:
        # Prefer verdict filter; also include status=REJECTED for safety
        rows = con.execute(
            """
            SELECT id, ts, symbol, side, qty, price, order_type, status, verdict, decision, action, meta_json
            FROM orders
            WHERE verdict='RISK_STOP_REQUIRED' OR status='REJECTED'
            ORDER BY id DESC
            """).fetchall()
    finally:
        con.close()

    total = len(rows)

    # Focus on RISK_STOP_REQUIRED subset
    stop_rows = []
    for r in rows:
        if (r["verdict"] or "") == "RISK_STOP_REQUIRED":
            stop_rows.append(r)

    n_stop = len(stop_rows)

    # Meta analysis
    key_ctr = Counter()
    nested_hint_ctr = Counter()
    symbol_ctr = Counter()
    order_type_ctr = Counter()
    side_ctr = Counter()

    # Trace hints (common names we hope exist in meta_json)
    TRACE_KEYS = [
        "strategy", "strategy_id", "strategy_name",
        "signal", "signal_id", "reason",
        "source", "source_file", "runner",
        "ref_price", "bid", "ask", "mid",
        "stop", "stop_price", "sl", "stop_loss",
        "take_profit", "tp",
    ]
    trace_values = defaultdict(Counter)

    samples = []
    for r in stop_rows[:2000]:
        symbol_ctr[r["symbol"]] += 1
        order_type_ctr[r["order_type"]] += 1
        side_ctr[r["side"]] += 1

        meta = safe_json_loads(r["meta_json"])
        for k in meta.keys():
            key_ctr[str(k)] += 1
            if "." in str(k):
                nested_hint_ctr[str(k).split(".")[0]] += 1

        for tk in TRACE_KEYS:
            if tk in meta and meta[tk] is not None:
                trace_values[tk][str(meta[tk])[:80]] += 1

        if len(samples) < 12:
            samples.append({
                "id": r["id"],
                "ts": r["ts"],
                "symbol": r["symbol"],
                "side": r["side"],
                "qty": r["qty"],
                "price": r["price"],
                "order_type": r["order_type"],
                "status": r["status"],
                "verdict": r["verdict"],
                "decision": r["decision"],
                "action": r["action"],
                "meta_keys": sorted(list(meta.keys()))[:60],
                "meta_excerpt": meta,
            })

    generated_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    def top(counter: Counter, n=20):
        return [(k, int(v)) for k, v in counter.most_common(n)]

    out = {
        "generated_utc": generated_utc,
        "db": str(DB),
        "scope": {
            "rows_scanned": total,
            "risk_stop_required_rows": n_stop,
        },
        "top": {
            "symbols": top(symbol_ctr, 20),
            "order_type": top(order_type_ctr, 10),
            "side": top(side_ctr, 5),
            "meta_keys": top(key_ctr, 40),
        },
        "trace_hints": {
            k: top(v, 10) for k, v in trace_values.items()
        },
        "samples_top12": samples,
        "notes": [
            "目標：把 stop-required 的拒單追溯到產生 order intent 的來源（strategy/signal/runner/source_file）。",
            "下一步將依 trace_hints 決定要你上傳哪個策略/runner 檔案做『策略層硬必填 stop』patch。",
        ],
    }

    OUT_JSON.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = []
    md.append("# Stop Required Audit (latest)\n\n")
    md.append(f"- Generated (UTC): {generated_utc}\n")
    md.append(f"- DB: `{DB}`\n")
    md.append(f"- rows_scanned: **{total}**\n")
    md.append(f"- verdict=RISK_STOP_REQUIRED: **{n_stop}**\n\n")

    md.append("## Top symbols\n")
    for k, v in out["top"]["symbols"]:
        md.append(f"- {k}: {v}\n")

    md.append("\n## Top meta keys (presence count)\n")
    for k, v in out["top"]["meta_keys"]:
        md.append(f"- {k}: {v}\n")

    md.append("\n## Trace hints (top values)\n")
    for tk, lst in out["trace_hints"].items():
        if not lst:
            continue
        md.append(f"\n### {tk}\n")
        for k, v in lst:
            md.append(f"- {k}: {v}\n")

    md.append("\n## Samples (top12)\n")
    md.append("```json\n")
    md.append(json.dumps(samples, ensure_ascii=False, indent=2))
    md.append("\n```\n")

    OUT_MD.write_text("".join(md), encoding="utf-8")

    write_sha256_sidecar(OUT_JSON)
    write_sha256_sidecar(OUT_MD)

    print(f"[OK] wrote: {OUT_JSON}")
    print(f"[OK] wrote: {OUT_MD}")
    print(f"[OK] sha256: {OUT_JSON}.sha256.txt")
    print(f"[OK] sha256: {OUT_MD}.sha256.txt")
    print(f"[OK] risk_stop_required_rows: {n_stop} / rows_scanned: {total}")

if __name__ == "__main__":
    main()
