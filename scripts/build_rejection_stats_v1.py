from __future__ import annotations
import argparse, json, sqlite3, hashlib
from pathlib import Path
from datetime import datetime, timezone

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def write_sha256_sidecar(p: Path) -> None:
    dig = sha256_file(p)
    side = p.with_name(p.name + ".sha256.txt")
    side.write_text(f"{dig}  {p.name}\n", encoding="utf-8")

def utc_now_z() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

def top_items(d: dict[str,int], n: int) -> list[tuple[str,int]]:
    return sorted(d.items(), key=lambda kv: (-kv[1], kv[0]))[:n]

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="runtime/data/tmf_autotrader_v1.sqlite3")
    ap.add_argument("--outdir", default="runtime/reports")
    ap.add_argument("--topn", type=int, default=30)
    ap.add_argument("--status", default="REJECTED")  # allow override for future
    args = ap.parse_args()

    db = Path(args.db)
    if not db.exists():
        raise SystemExit(f"[FATAL] missing db: {db}")

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(str(db))
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            """
            SELECT ts, symbol, side, qty, price, order_type, status, verdict, decision, action, meta_json
            FROM orders
            WHERE status = ?
            ORDER BY ts DESC
            """,
            (args.status,),
        ).fetchall()
    finally:
        con.close()

    total = len(rows)

    def inc(m: dict, k: str) -> None:
        if k is None:
            return
        k = str(k).strip()
        if not k:
            return
        m[k] = int(m.get(k, 0)) + 1

    by_status: dict[str,int] = {}
    by_decision: dict[str,int] = {}
    by_verdict: dict[str,int] = {}
    by_action: dict[str,int] = {}
    by_exec_code: dict[str,int] = {}
    by_reason: dict[str,int] = {}

    dpbm_like = 0
    taifex_like = 0

    samples: list[dict] = []
    for r in rows[: min(300, total)]:
        status  = r["status"]
        verdict = r["verdict"]
        decision = r["decision"]
        action  = r["action"]

        inc(by_status, status)
        inc(by_verdict, verdict)
        inc(by_decision, decision)
        inc(by_action, action)

        meta = {}
        try:
            meta = json.loads(r["meta_json"] or "{}") if isinstance(r["meta_json"], str) else {}
        except Exception:
            meta = {}

        exec_code = ""
        reason = ""

        # prefer structured reject_decision / preflight_verdict if present
        rd = meta.get("reject_decision") if isinstance(meta, dict) else None
        if isinstance(rd, dict):
            exec_code = str(rd.get("code") or "")
            reason = str(rd.get("reason") or "")

        if not exec_code:
            pv = meta.get("preflight_verdict") if isinstance(meta, dict) else None
            if isinstance(pv, dict):
                exec_code = str(pv.get("code") or "")
                if not reason:
                    reason = str(pv.get("reason") or "")

        # fallback: sometimes legacy rows only have verdict string
        if not exec_code and isinstance(verdict, str) and verdict.startswith("RISK_"):
            exec_code = verdict

        if exec_code:
            inc(by_exec_code, exec_code)
            u = exec_code.upper()
            if "TAIFEX" in u or u.startswith("EXEC_TAIFEX"):
                taifex_like += 1
            if "DPB" in u or "DPBM" in u:
                dpbm_like += 1

        if reason:
            inc(by_reason, reason[:200])

        samples.append({
            "ts": r["ts"],
            "symbol": r["symbol"],
            "side": r["side"],
            "qty": r["qty"],
            "order_type": r["order_type"],
            "status": status,
            "verdict": verdict,
            "decision": decision,
            "action": action,
            "exec_code": exec_code,
            "reason": reason,
        })

    report = {
        "generated_utc": utc_now_z(),
        "db": str(db),
        "filter": {"status": args.status},
        "total_rows": total,
        "counts": {
            "by_status_top": top_items(by_status, args.topn),
            "by_decision_top": top_items(by_decision, args.topn),
            "by_verdict_top": top_items(by_verdict, args.topn),
            "by_action_top": top_items(by_action, args.topn),
            "by_exec_code_top": top_items(by_exec_code, args.topn),
            "by_reason_top": top_items(by_reason, args.topn),
        },
        "taifex_like_rejects_sampled": taifex_like,
        "dpbm_like_rejects_sampled": dpbm_like,
        "sample_recent": samples[:80],
    }

    out_json = outdir / "rejection_stats_latest.json"
    out_md   = outdir / "rejection_stats_latest.md"

    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md = []
    md.append("# Rejection Stats (latest)\n\n")
    md.append(f"- Generated (UTC): {report['generated_utc']}\n")
    md.append(f"- DB: `{report['db']}`\n")
    md.append(f"- Filter: status=`{args.status}`\n")
    md.append(f"- Total rows: **{total}**\n")
    md.append(f"- TAIFEX-like sampled: **{taifex_like}**\n")
    md.append(f"- DPBM-like sampled: **{dpbm_like}**\n")

    md.append("\n## Top by verdict\n")
    for k,v in report['counts']["by_verdict_top"]:
        md.append(f"- {k}: {v}\n")

    md.append("\n## Top by decision\n")
    for k,v in report['counts']["by_decision_top"]:
        md.append(f"- {k}: {v}\n")

    md.append("\n## Top by action\n")
    for k,v in report['counts']["by_action_top"]:
        md.append(f"- {k}: {v}\n")

    md.append("\n## Top by exec_code (meta_json/reject_decision/preflight_verdict)\n")
    for k,v in report['counts']["by_exec_code_top"]:
        md.append(f"- {k}: {v}\n")

    md.append("\n## Top by reason (best-effort)\n")
    for k,v in report['counts']["by_reason_top"]:
        md.append(f"- {k}: {v}\n")

    out_md.write_text("".join(md), encoding="utf-8")

    write_sha256_sidecar(out_json)
    write_sha256_sidecar(out_md)

    print("[OK] total_rows:", total)
    print("[OK] wrote:", out_json)
    print("[OK] wrote:", out_md)
    print("[OK] sha256:", out_json.with_name(out_json.name + ".sha256.txt"))
    print("[OK] sha256:", out_md.with_name(out_md.name + ".sha256.txt"))

if __name__ == "__main__":
    main()
