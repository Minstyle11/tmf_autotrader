#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Daily Report v1 (TMF AutoTrader)
- Reads runtime/data/tmf_autotrader_v1.sqlite3
- Emits runtime/ops/daily_report/DR_YYYY-MM-DD.md + .sha256
- Emits runtime/ops/daily_report/DR_YYYY-MM-DD.json + .sha256

Design goals:
- Append-only artifacts (new file per day)
- Idempotent per-day regeneration (same day overwrites same DR_* files only)
- No external deps; Python stdlib only

v1.1 patch (2026-02-17):
- Integrate runtime/reports/rejection_stats_latest.json into diagnostics + markdown
  so rejection governance is visible daily (Risk/Safety gates, DPBM/TAIFEX-like).
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
import json, os, sqlite3, hashlib

DB_DEFAULT = Path("runtime/data/tmf_autotrader_v1.sqlite3")
OUTDIR = Path("runtime/ops/daily_report")

REJ_STATS_JSON = Path("runtime/reports/rejection_stats_latest.json")

def _now_local_str() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")

def _today_ymd_local() -> str:
    return datetime.now().astimezone().strftime("%Y-%m-%d")

def _sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def _write_sidecar_sha256(p: Path) -> None:
    dig = _sha256_file(p)
    side = p.with_suffix(p.suffix + ".sha256.txt")
    side.write_text(f"{dig}  {p.name}\n", encoding="utf-8")

def _table_exists(con: sqlite3.Connection, name: str) -> bool:
    r = con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
    return r is not None

def _count(con: sqlite3.Connection, sql: str, args=()) -> int:
    r = con.execute(sql, args).fetchone()
    return int(r[0]) if r and r[0] is not None else 0

def _fetchall(con: sqlite3.Connection, sql: str, args=()):
    con.row_factory = sqlite3.Row
    return con.execute(sql, args).fetchall()

def _safe_read_rejection_stats() -> dict | None:
    """
    Best-effort read of rejection_stats_latest.json.
    Never raise; daily report must still emit even if rejection stats missing/broken.
    """
    if not REJ_STATS_JSON.exists():
        return None
    try:
        data = json.loads(REJ_STATS_JSON.read_text(encoding="utf-8"))
    except Exception as e:
        return {"_error": f"failed_to_parse_rejection_stats: {type(e).__name__}: {e}"}

    counts = data.get("counts") or {}
    by_verdict = counts.get("by_verdict_top") or []
    by_reason  = counts.get("by_reason_top") or []
    by_status  = counts.get("by_status_top") or []
    by_decision = counts.get("by_decision_top") or []
    by_action = counts.get("by_action_top") or []
    by_exec_code = counts.get("by_exec_code_top") or []

    # convert top lists to compact dict (top 12)
    def topdict(lst, n=12):
        out = {}
        for k, v in lst[:n]:
            out[str(k)] = int(v)
        return out

    return {
        "generated_utc": data.get("generated_utc"),
        "db": data.get("db"),
        "filter": data.get("filter"),
        "total_rows": int(data.get("total_rows") or 0),
        "dpbm_like_rejects_sampled": int(data.get("dpbm_like_rejects_sampled") or 0),
        "taifex_like_rejects_sampled": int(data.get("taifex_like_rejects_sampled") or 0),
        "top": {
            "status": topdict(by_status),
            "verdict": topdict(by_verdict),
            "decision": topdict(by_decision),
            "action": topdict(by_action),
            "exec_code": topdict(by_exec_code),
            "reason": topdict(by_reason),
        },
        "path": str(REJ_STATS_JSON),
        "sha256": _sha256_file(REJ_STATS_JSON),
    }

@dataclass
class DailyReport:
    ymd: str
    ts_generated_local: str
    db_path: str
    summary: dict
    diagnostics: dict
    samples: dict

def main():
    db = Path(os.environ.get("TMF_DB_PATH", str(DB_DEFAULT)))
    if not db.exists():
        raise SystemExit(f"[FAIL] missing db: {db}")

    OUTDIR.mkdir(parents=True, exist_ok=True)
    ymd = os.environ.get("TMF_REPORT_DATE", _today_ymd_local())
    ts_local = _now_local_str()

    con = sqlite3.connect(str(db))
    try:
        # --- core counts (best-effort; tolerate missing tables) ---
        tables = {
            "events": _table_exists(con, "events"),
            "orders": _table_exists(con, "orders"),
            "fills": _table_exists(con, "fills"),
            "trades": _table_exists(con, "trades"),
            "health_checks": _table_exists(con, "health_checks"),
        }

        # day filter: we store ISO-ish timestamps; best-effort prefix match on YYYY-MM-DD
        like = f"{ymd}%"

        summary = {
            "tables_present": tables,
            "counts": {},
        }

        if tables["events"]:
            summary["counts"]["events_total"] = _count(con, "SELECT COUNT(*) FROM events")
            summary["counts"]["events_today"] = _count(con, "SELECT COUNT(*) FROM events WHERE ts LIKE ?", (like,))
        if tables["orders"]:
            summary["counts"]["orders_total"] = _count(con, "SELECT COUNT(*) FROM orders")
            summary["counts"]["orders_today"] = _count(con, "SELECT COUNT(*) FROM orders WHERE ts LIKE ?", (like,))
        if tables["fills"]:
            summary["counts"]["fills_total"] = _count(con, "SELECT COUNT(*) FROM fills")
            summary["counts"]["fills_today"] = _count(con, "SELECT COUNT(*) FROM fills WHERE ts LIKE ?", (like,))
        if tables["trades"]:
            summary["counts"]["trades_total"] = _count(con, "SELECT COUNT(*) FROM trades")
            summary["counts"]["trades_today"] = _count(con, "SELECT COUNT(*) FROM trades WHERE open_ts LIKE ?", (like,))
        if tables["health_checks"]:
            summary["counts"]["health_checks_total"] = _count(con, "SELECT COUNT(*) FROM health_checks")
            summary["counts"]["health_checks_today"] = _count(con, "SELECT COUNT(*) FROM health_checks WHERE ts LIKE ?", (like,))

        # --- diagnostics (simple but high-signal) ---
        diagnostics = {}

        # A) latest health check status by name (top 10 recent)
        if tables["health_checks"]:
            rows = _fetchall(con,
                "SELECT id, ts, kind, check_name, status FROM health_checks ORDER BY id DESC LIMIT 10"
            )
            diagnostics["latest_health_checks_top10"] = [dict(r) for r in rows]
            diagnostics["health_fail_recent"] = [dict(r) for r in rows if str(r["status"]).upper() not in ("OK","PASS","SUCCESS")]

        # B) market quality: how often spread gate rejects appeared in today logs? (best-effort via events payload search)
        if tables["events"]:
            diagnostics["risk_spread_too_wide_events_today"] = _count(
                con,
                "SELECT COUNT(*) FROM events WHERE ts LIKE ? AND payload_json LIKE ?", (like, "%RISK_SPREAD_TOO_WIDE%")
            )

        # C) data freshness proxy: latest bidask_fop_v1 age (if present)
        if tables["events"]:
            con.row_factory = sqlite3.Row
            r = con.execute(
                "SELECT id, ts, kind, source_file FROM events WHERE kind='bidask_fop_v1' ORDER BY ts DESC LIMIT 1"
            ).fetchone()
            diagnostics["latest_bidask_fop_v1"] = dict(r) if r else None

        # D) rejection governance (from rejection_stats_latest.json)
        rej = _safe_read_rejection_stats()
        diagnostics["rejection_stats_latest"] = rej
        if isinstance(rej, dict) and "top" in rej:
            v = rej["top"].get("verdict", {}) or {}
            # Promote a few critical gates to explicit diagnostics fields for human scanning
            diagnostics["rej_counts_key"] = {
                "RISK_STOP_REQUIRED": int(v.get("RISK_STOP_REQUIRED", 0)),
                "SAFETY_FEED_STALE": int(v.get("SAFETY_FEED_STALE", 0)),
                "SAFETY_COOLDOWN_ACTIVE": int(v.get("SAFETY_COOLDOWN_ACTIVE", 0)),
            }

        # --- samples (for human read) ---
        samples = {}
        if tables["events"]:
            rows = _fetchall(con, "SELECT id, ts, kind, source_file FROM events ORDER BY id DESC LIMIT 8")
            samples["events_tail8"] = [dict(r) for r in rows]
        if tables["trades"]:
            rows = _fetchall(con, "SELECT id, open_ts, close_ts, symbol, side, qty, entry, exit, pnl FROM trades ORDER BY id DESC LIMIT 8")
            samples["trades_tail8"] = [dict(r) for r in rows]

        rep = DailyReport(
            ymd=ymd,
            ts_generated_local=ts_local,
            db_path=str(db),
            summary=summary,
            diagnostics=diagnostics,
            samples=samples,
        )

        # --- write JSON ---
        out_json = OUTDIR / f"DR_{ymd}.json"
        out_json.write_text(json.dumps(rep.__dict__, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        _write_sidecar_sha256(out_json)

        # --- write MD ---
        out_md = OUTDIR / f"DR_{ymd}.md"
        md = []
        md.append(f"# Daily Report v1 — {ymd}")
        md.append("")
        md.append(f"- generated_at: {ts_local}")
        md.append(f"- db_path: `{rep.db_path}`")
        md.append("")

        md.append("## Summary")
        md.append("```json")
        md.append(json.dumps(rep.summary, ensure_ascii=False, indent=2))
        md.append("```")
        md.append("")

        md.append("## Diagnostics")
        md.append("```json")
        md.append(json.dumps(rep.diagnostics, ensure_ascii=False, indent=2))
        md.append("```")
        md.append("")

        # Human-friendly rejection summary section (key for governance)
        md.append("## Rejection Stats (latest)")
        if rej is None:
            md.append("- rejection_stats_latest.json not found")
        elif isinstance(rej, dict) and rej.get("_error"):
            md.append(f"- ERROR: {rej.get(_error)}")
        elif isinstance(rej, dict):
            md.append(f"- source: `{rej.get('path')}`")
            md.append(f"- sha256: `{rej.get('sha256')}`")
            md.append(f"- generated_utc: `{rej.get('generated_utc')}`")
            md.append(f"- total_rows: **{rej.get('total_rows')}**")
            md.append(f"- dpbm_like_rejects_sampled: **{rej.get('dpbm_like_rejects_sampled')}**")
            md.append(f"- taifex_like_rejects_sampled: **{rej.get('taifex_like_rejects_sampled')}**")
            md.append("")
            md.append("### Top verdicts (top12)")
            for k, v in (rej.get("top", {}).get("verdict", {}) or {}).items():
                md.append(f"- {k}: {v}")
            md.append("")
            md.append("### Top reasons (top12, best-effort)")
            for k, v in (rej.get("top", {}).get("reason", {}) or {}).items():
                md.append(f"- {k}: {v}")
        else:
            md.append("- rejection stats in unexpected format")
        md.append("")

        md.append("## Samples")
        md.append("```json")
        md.append(json.dumps(rep.samples, ensure_ascii=False, indent=2))
        md.append("```")
        md.append("")
        out_md.write_text("\n".join(md) + "\n", encoding="utf-8")
        _write_sidecar_sha256(out_md)

        print(f"[OK] wrote: {out_md}")
        print(f"[OK] wrote: {out_md}.sha256.txt")
        print(f"[OK] wrote: {out_json}")
        print(f"[OK] wrote: {out_json}.sha256.txt")

    finally:
        con.close()

if __name__ == "__main__":
    main()
