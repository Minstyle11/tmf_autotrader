from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from src.safety.system_safety_v1 import SafetyConfigV1, SystemSafetyEngineV1


def _iso(dt: datetime) -> str:
    # keep timezone info (SystemSafetyEngineV1 tolerates Z / +00:00)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat(timespec="milliseconds")


def _ensure_events_schema(con: sqlite3.Connection) -> None:
    con.execute(
        "CREATE TABLE IF NOT EXISTS events("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "ts TEXT NOT NULL,"
        "kind TEXT NOT NULL,"
        "payload_json TEXT NOT NULL,"
        "source_file TEXT"
        ")"
    )
    con.commit()


def _insert_bidask(con: sqlite3.Connection, *, ts: str, code: str = "TMFB6", source_file: str = "chaos_drill") -> None:
    payload = {
        "code": code,
        "bid": 31774.0,
        "ask": 31775.0,
        # SystemSafetyEngineV1 uses recv_ts/ingest_ts if present for feed_age_ms
        "ingest_ts": ts,
    }
    con.execute(
        "INSERT INTO events(ts, kind, payload_json, source_file) VALUES(?,?,?,?)",
        (ts, "bidask_fop_v1", json.dumps(payload, ensure_ascii=False), source_file),
    )
    con.commit()


@dataclass
class Scenario:
    name: str
    # how old the last bidask is (ms). If None -> insert fresh bidask.
    bidask_age_ms: Optional[int]
    meta: Dict[str, Any]
    expect_code: str  # verdict.code


def run_drills(out_json: str, out_log: str) -> Dict[str, Any]:
    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    os.makedirs(os.path.dirname(out_log), exist_ok=True)

    now = datetime.now(timezone.utc)

    # Build a temp DB that matches SystemSafetyEngineV1 expectations (events table)
    tmpdir = tempfile.mkdtemp(prefix="tmf_chaos_drill_v1.")
    db_path = os.path.join(tmpdir, "tmf_chaos_drill.sqlite3")

    con = sqlite3.connect(db_path)
    try:
        _ensure_events_schema(con)

        cfg = SafetyConfigV1(
            require_recent_bidask=1,
            bidask_kind="bidask_fop_v1",
            reject_synthetic_bidask=1,
            fop_code="TMFB6",
            # keep loose here; the drill is about latency/backpressure (OS-1), not stale-feed gate
            max_bidask_age_seconds=6 * 60 * 60,
            require_session_open=0,
        )
        ss = SystemSafetyEngineV1(db_path=db_path, cfg=cfg)
        # deterministic reset
        ss.clear_cooldown()
        ss.clear_kill()

        scenarios: List[Scenario] = [
            Scenario("baseline_ok", bidask_age_ms=0, meta={"broker_rtt_ms": 10, "oms_queue_depth": 0}, expect_code="OK"),
            # cooldown by feed staleness (threshold default 1500ms)
            Scenario("cooldown_feed_age", bidask_age_ms=2500, meta={"broker_rtt_ms": 0, "oms_queue_depth": 0}, expect_code="SAFETY_COOLDOWN_ACTIVE"),
            Scenario("cooldown_broker_rtt", bidask_age_ms=0, meta={"broker_rtt_ms": 5000, "oms_queue_depth": 0}, expect_code="SAFETY_COOLDOWN_ACTIVE"),
            Scenario("cooldown_queue_depth", bidask_age_ms=0, meta={"broker_rtt_ms": 0, "oms_queue_depth": 999}, expect_code="SAFETY_COOLDOWN_ACTIVE"),
            # kill on extreme blindness (BackpressureGovernor: feed_age_ms >= 5000ms)
            Scenario("kill_extreme_feed_age", bidask_age_ms=6000, meta={"broker_rtt_ms": 0, "oms_queue_depth": 0}, expect_code="SAFETY_KILL_SWITCH"),
        ]

        lines: List[str] = []
        results: List[Dict[str, Any]] = []

        for sc in scenarios:
            # reset safety state between scenarios (avoid bleed-through)
            ss.clear_cooldown()
            ss.clear_kill()

            # seed bidask
            if sc.bidask_age_ms is None:
                ts = _iso(now)
            else:
                ts = _iso(now - timedelta(milliseconds=int(sc.bidask_age_ms)))
            _insert_bidask(con, ts=ts)

            v = ss.check_pre_trade(meta=sc.meta)
            ok = (str(v.code) == str(sc.expect_code))
            results.append(
                {
                    "name": sc.name,
                    "expected_code": sc.expect_code,
                    "observed": {"ok": bool(v.ok), "code": str(v.code), "reason": str(v.reason)},
                    "pass": bool(ok),
                }
            )
            lines.append(f"[{sc.name}] expected={sc.expect_code} observed={v.code} ok={ok}")

            if not ok:
                # fail-fast: record and stop
                break

        summary = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "db_path": db_path,
            "results": results,
            "pass": all(r["pass"] for r in results) if results else False,
        }

        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        with open(out_log, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
            f.write(f"[ARTIFACT] json={out_json}\n")
            f.write(f"[ARTIFACT] log={out_log}\n")
            f.write(f"[ARTIFACT] tmpdb={db_path}\n")

        return summary
    finally:
        con.close()


def main() -> None:
    out_json = os.getenv("TMF_CHAOS_DRILL_OUT_JSON", "runtime/logs/chaos_drill_v1.latest.json")
    out_log  = os.getenv("TMF_CHAOS_DRILL_OUT_LOG",  "runtime/logs/chaos_drill_v1.latest.log")
    summary = run_drills(out_json, out_log)
    if not summary.get("pass"):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
