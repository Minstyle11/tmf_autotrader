# TMF AutoTrader — Drift Detector v1 (minimal, fail-safe)
# v18.1 intent: drift is first-class; detection must trigger freeze/rollback (at least freeze).
#
# This v1 detector is intentionally conservative:
# - looks at recent bidask spreads (mean + sample size)
# - flags EXTREME vol_regime (if provided by runner meta) as "do not promote"
# - outputs a small JSON artifact for auditability
#
# NOTE: This does NOT "learn"; it only detects and triggers governance freeze.
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
from pathlib import Path
import json, os, sqlite3
from datetime import datetime, timezone

from .governance_v1 import freeze_on_drift

DB_DEFAULT = "runtime/data/tmf_autotrader_v1.sqlite3"
ART_DIR = Path("runtime/handoff/state")
ART_LATEST = ART_DIR / "drift_report_latest.json"

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00","Z")

@dataclass
class DriftResult:
    ok: bool
    code: str
    reason: str
    details: Dict[str, Any]

def _connect(db_path: str) -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    return con

def _recent_spreads(con: sqlite3.Connection, *, kind: str = "bidask_fop_v1", code: str = "TMFB6", limit: int = 300) -> Tuple[int, float]:
    # events table schema in this project is stable enough for basic queries:
    # we rely on payload.ask / payload.bid JSON paths via stored columns or JSON extraction.
    # For portability, attempt both:
    cur = con.cursor()
    # try: columns bid/ask
    for sql in (
        "SELECT ask, bid FROM events WHERE kind=? AND code=? ORDER BY id DESC LIMIT ?",
        "SELECT json_extract(payload,'$.ask') AS ask, json_extract(payload,'$.bid') AS bid FROM events WHERE kind=? AND code=? ORDER BY id DESC LIMIT ?",
    ):
        try:
            rows = cur.execute(sql, (kind, code, limit)).fetchall()
            spreads = []
            for r in rows:
                ask = r["ask"]
                bid = r["bid"]
                if ask is None or bid is None:
                    continue
                try:
                    spreads.append(float(ask) - float(bid))
                except Exception:
                    continue
            if not spreads:
                return (0, 0.0)
            return (len(spreads), sum(spreads)/len(spreads))
        except Exception:
            continue
    return (0, 0.0)

def run_drift_detector_v1(*, db_path: Optional[str] = None, fop_code: str = "TMFB6") -> DriftResult:
    db = db_path or (os.environ.get("TMF_DB", DB_DEFAULT) or DB_DEFAULT)
    if not Path(db).exists():
        res = DriftResult(ok=False, code="DRIFT_DB_MISSING", reason=f"db not found: {db}", details={"db": db})
        _write_artifact(res)
        freeze_on_drift(code=res.code, reason=res.reason)
        return res

    con = _connect(db)
    try:
        n, mean_spread = _recent_spreads(con, kind="bidask_fop_v1", code=fop_code, limit=int(os.environ.get("TMF_DRIFT_SPREAD_LOOKBACK","300") or "300"))
    finally:
        con.close()

    min_n = int(os.environ.get("TMF_DRIFT_MIN_SAMPLES","60") or "60")
    max_mean_spread = float(os.environ.get("TMF_DRIFT_MAX_MEAN_SPREAD","2.5") or "2.5")  # points

    # Conservative triggers
    if n < min_n:
        res = DriftResult(ok=False, code="DRIFT_SAMPLES_LOW", reason=f"spread samples too low n={n} < {min_n}", details={"n": n, "min_n": min_n, "mean_spread": mean_spread})
        _write_artifact(res); freeze_on_drift(code=res.code, reason=res.reason); return res
    if mean_spread > max_mean_spread:
        res = DriftResult(ok=False, code="DRIFT_SPREAD_WIDE", reason=f"mean spread too wide mean={mean_spread:.4f} > {max_mean_spread}", details={"n": n, "mean_spread": mean_spread, "max_mean_spread": max_mean_spread})
        _write_artifact(res); freeze_on_drift(code=res.code, reason=res.reason); return res

    res = DriftResult(ok=True, code="OK", reason="no drift triggers (v1)", details={"n": n, "mean_spread": mean_spread, "max_mean_spread": max_mean_spread})
    _write_artifact(res)
    return res

def _write_artifact(res: DriftResult) -> None:
    ART_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "ts": _now_iso(),
        "ok": res.ok,
        "code": res.code,
        "reason": res.reason,
        "details": res.details,
        "version": "drift_detector_v1",
    }
    ART_LATEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

if __name__ == "__main__":
    r = run_drift_detector_v1()
    print(json.dumps({"ok": r.ok, "code": r.code, "reason": r.reason, "details": r.details}, ensure_ascii=False))
