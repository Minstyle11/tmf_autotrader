from __future__ import annotations
import json
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime, time, timezone
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class SafetyConfigV1:
    # feed / event truth source guard
    require_recent_bidask: int = 1
    bidask_kind: str = "bidask_fop_v1"
    fop_code: str = "TMFB6"
    max_bidask_age_seconds: int = 6 * 60 * 60  # dev-safe default: 6h (tighten later in live)

    # session guard (TW futures typical day session); can be relaxed/overridden later
    require_session_open: int = 0
    session_open_hhmm: str = "0845"
    session_close_hhmm: str = "1345"

    # manual halt list (expiry/settlement/maintenance days) -> YYYY-MM-DD
    halt_dates_csv: str = ""


@dataclass(frozen=True)
class SafetyVerdictV1:
    ok: bool
    code: str
    reason: str
    details: Dict[str, Any]


def _parse_hhmm(s: str) -> time:
    s = str(s).strip()
    if len(s) != 4 or not s.isdigit():
        return time(0, 0)
    return time(int(s[:2]), int(s[2:]))


def _today_ymd(now: Optional[datetime] = None) -> str:
    now = now or datetime.now()
    return now.strftime("%Y-%m-%d")


def _in_session(cfg: SafetyConfigV1, now: Optional[datetime] = None) -> bool:
    now = now or datetime.now()
    o = _parse_hhmm(cfg.session_open_hhmm)
    c = _parse_hhmm(cfg.session_close_hhmm)
    tnow = now.time()
    return (tnow >= o) and (tnow <= c)


def _is_halt_day(cfg: SafetyConfigV1, now: Optional[datetime] = None) -> bool:
    if not cfg.halt_dates_csv.strip():
        return False
    day = _today_ymd(now)
    items = [x.strip() for x in cfg.halt_dates_csv.split(",") if x.strip()]
    return day in set(items)


def _loads(s: Any) -> Dict[str, Any]:
    if not s:
        return {}
    if isinstance(s, dict):
        return s
    try:
        return json.loads(s) if isinstance(s, str) else {}
    except Exception:
        return {}


class SystemSafetyEngineV1:
    """
    v1 goals (aligned with v18 mainline OS priorities):
    - Guard against stale quote feed using ONLY DB events as truth source.
    - Optional session open/close guard.
    - Optional manual halt/expiry days list (patchable via config later).
    """
    def __init__(self, *, db_path: str, cfg: Optional[SafetyConfigV1] = None):
        self.db_path = str(db_path)
        self.cfg = cfg or SafetyConfigV1()

    def _con(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def _latest_event_by_code(self, con: sqlite3.Connection, *, kind: str, code: str, scan_limit: int = 2000, reject_synthetic: bool = True) -> Optional[Tuple[int, str, Dict[str, Any]]]:
        rows = con.execute(
            "SELECT id, ts, payload_json FROM events WHERE kind=? ORDER BY ts DESC, id DESC LIMIT ?",
            (str(kind), int(scan_limit)),
        ).fetchall()
        for r in rows:
            payload = _loads(r["payload_json"])
            if str(payload.get("code", "")) == str(code):
                if reject_synthetic and bool(payload.get("synthetic")):
                    continue
                return (int(r["id"]), str(r["ts"]), payload)
        return None

    def _age_seconds(self, ts_iso: str, now: Optional[datetime] = None) -> Optional[float]:
        try:
            s = str(ts_iso).strip()
            # tolerate Z suffix (UTC)
            if s.endswith("Z"):
                s = s[:-1] + "+00:00"
            dt = datetime.fromisoformat(s)

            if now is None:
                # If dt is timezone-aware, use timezone-aware now in same tz; else naive now
                now = datetime.now(dt.tzinfo) if dt.tzinfo is not None else datetime.now()
            else:
                # Align tz awareness between now and dt
                if dt.tzinfo is not None and now.tzinfo is None:
                    now = now.replace(tzinfo=dt.tzinfo)
                if dt.tzinfo is None and now.tzinfo is not None:
                    dt = dt.replace(tzinfo=now.tzinfo)

            return float((now - dt).total_seconds())
        except Exception:
            return None

    def check_pre_trade(self, *, meta: Optional[Dict[str, Any]] = None) -> SafetyVerdictV1:
            meta = meta or {}
            cfg = self.cfg
    
            # A) Manual halt day (expiry/maintenance)
            if _is_halt_day(cfg):
                return SafetyVerdictV1(
                    False,
                    "SAFETY_HALT_DAY",
                    "today is configured as a halt/expiry/maintenance day; trading blocked",
                    {"today": _today_ymd(), "halt_dates_csv": cfg.halt_dates_csv},
                )
    
            # B) Session guard (optional)
            if cfg.require_session_open == 1 and (not _in_session(cfg)):
                return SafetyVerdictV1(
                    False,
                    "SAFETY_SESSION_CLOSED",
                    "session guard active and current time is outside session window",
                    {"open_hhmm": cfg.session_open_hhmm, "close_hhmm": cfg.session_close_hhmm},
                )
    
            # C) Feed staleness guard from DB events (truth source)
            if cfg.require_recent_bidask == 1:
                con = self._con()
                try:
                    ev = self._latest_event_by_code(con, kind=cfg.bidask_kind, code=cfg.fop_code, reject_synthetic=True)
                finally:
                    con.close()
    
                if not ev:
                    return SafetyVerdictV1(
                        False,
                        "SAFETY_BIDASK_MISSING",
                        "no bidask event found in DB for required fop_code",
                        {"bidask_kind": cfg.bidask_kind, "fop_code": cfg.fop_code},
                    )
    
                event_id, ts, payload = ev
                age = self._age_seconds(ts)
                if age is None:
                    return SafetyVerdictV1(
                        False,
                        "SAFETY_BIDASK_TS_INVALID",
                        "cannot parse bidask event ts",
                        {"bidask_event_id": event_id, "ts": ts},
                    )
    
                if age > float(cfg.max_bidask_age_seconds):
                    return SafetyVerdictV1(
                        False,
                        "SAFETY_FEED_STALE",
                        f"bidask feed stale: age_sec={age:.1f} > max={cfg.max_bidask_age_seconds}",
                        {
                            "bidask_event_id": event_id,
                            "bidask_ts": ts,
                            "age_seconds": age,
                            "max_bidask_age_seconds": cfg.max_bidask_age_seconds,
                            "fop_code": cfg.fop_code,
                        },
                    )
    
            return SafetyVerdictV1(True, "OK", "system safety pre-trade pass", {"cfg": asdict(cfg)})
