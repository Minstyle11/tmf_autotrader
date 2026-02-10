from __future__ import annotations
import json
import sqlite3
import os
from dataclasses import dataclass, asdict
from datetime import datetime, time, timezone
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class SafetyConfigV1:
    # feed / event truth source guard
    require_recent_bidask: int = 1
    bidask_kind: str = "bidask_fop_v1"
    reject_synthetic_bidask: int = 1  # default: reject synthetic bidask; allow only in explicit offline smoke
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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": bool(self.ok),
            "code": str(self.code),
            "reason": str(self.reason),
            "details": dict(self.details) if isinstance(self.details, dict) else {"_raw": str(self.details)},
        }


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


def _env_truthy(name: str, default: str = "0") -> bool:
    v = str(os.getenv(name, default) or "").strip().lower()
    return v in {"1","true","t","yes","y","on"}

def _loads(s: Any) -> Dict[str, Any]:
    if not s:
        return {}
    if isinstance(s, dict):
        return s
    try:
        return json.loads(s) if isinstance(s, str) else {}
    except Exception:
        return {}



    def to_dict(self):
        return {
            "ok": bool(self.ok),
            "code": str(self.code),
            "reason": str(self.reason),
            "details": self.details,
        }
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

    def _ensure_safety_state_table(self, con: sqlite3.Connection) -> None:
        con.execute(
            "CREATE TABLE IF NOT EXISTS safety_state("
            "key TEXT PRIMARY KEY,"
            "value_json TEXT,"
            "ts TEXT"
            ")"
        )

    def _get_state(self, key: str) -> Optional[Dict[str, Any]]:
        try:
            con = self._con()
            try:
                self._ensure_safety_state_table(con)
                r = con.execute("SELECT value_json FROM safety_state WHERE key=?", (str(key),)).fetchone()
                if not r:
                    return None
                try:
                    return json.loads(r[0]) if r[0] else None
                except Exception:
                    return None
            finally:
                con.close()
        except Exception:
            return None

    def _set_state(self, key: str, value: Dict[str, Any]) -> None:
        con = self._con()
        try:
            self._ensure_safety_state_table(con)
            con.execute(
                "INSERT INTO safety_state(key, value_json, ts) VALUES(?,?,?) "
                "ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, ts=excluded.ts",
                (str(key), json.dumps(value, ensure_ascii=False), datetime.now().isoformat(timespec="seconds")),
            )
            con.commit()
        finally:
            con.close()

    def request_cooldown(self, *, seconds: int, code: str, reason: str, details: Optional[Dict[str, Any]] = None) -> None:
        details = details or {}
        # IMPORTANT: seconds<=0 means explicit clear (used by offline smoke / operator reset).
        # Do NOT coerce to 1 second; that causes immediate SAFETY_COOLDOWN_ACTIVE cascades.
        if int(seconds) <= 0:
            self._set_state("cooldown", {"until_epoch": 0, "code": str(code), "reason": str(reason), "details": details})
            return
        until = datetime.now().timestamp() + float(int(seconds))
        self._set_state("cooldown", {"until_epoch": until, "code": str(code), "reason": str(reason), "details": details})

    def request_kill(self, *, code: str, reason: str, details: Optional[Dict[str, Any]] = None) -> None:
        details = details or {}
        # kill switch stays until manually cleared
        self._set_state("kill", {"enabled": True, "code": str(code), "reason": str(reason), "details": details})

    def clear_cooldown(self) -> None:
        self._set_state("cooldown", {"until_epoch": 0})

    def clear_kill(self) -> None:
        self._set_state("kill", {"enabled": False})

    def _con(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.db_path)
        con.row_factory = sqlite3.Row
        return con

    def _latest_event_by_code(self, con: sqlite3.Connection, *, kind: str, code: str, scan_limit: int = 2000, reject_synthetic: bool = True) -> Optional[Tuple[int, str, Dict[str, Any]]]:
        rows = con.execute(
            "SELECT id, ts, payload_json FROM events WHERE kind=? ORDER BY id DESC LIMIT ?",
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

            # 0) global safety-state guards (cooldown / kill-switch)
            st_kill = self._get_state("kill") or {}
            if bool(st_kill.get("enabled")):
                return SafetyVerdictV1(
                    False,
                    "SAFETY_KILL_SWITCH",
                    "kill-switch enabled; trading blocked",
                    {"kill": st_kill},
                )

            st_cd = self._get_state("cooldown") or {}
            try:
                until = float(st_cd.get("until_epoch", 0) or 0)
            except Exception:
                until = 0.0
            now_ep = datetime.now().timestamp()
            if until > now_ep:
                return SafetyVerdictV1(
                    False,
                    "SAFETY_COOLDOWN_ACTIVE",
                    "cooldown active; trading blocked temporarily",
                    {"cooldown": st_cd, "now_epoch": now_ep},
                )
    
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
                    ev = self._latest_event_by_code(con, kind=cfg.bidask_kind, code=cfg.fop_code, reject_synthetic=bool(getattr(cfg,"reject_synthetic_bidask",1)))
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

                # Freshness should be based on receiver time (recv_ts) if available; ts can be market/event time.
                ts_used = None
                try:
                    if isinstance(payload, dict):
                        ts_used = payload.get("recv_ts") or payload.get("ingest_ts") or ts
                    else:
                        ts_used = ts
                except Exception:
                    ts_used = ts

                age = self._age_seconds(str(ts_used))
                if age is None:
                    return SafetyVerdictV1(
                        False,
                        "SAFETY_BIDASK_TS_INVALID",
                        "cannot parse bidask event ts",
                        {"bidask_event_id": event_id, "ts": ts, "ts_used": str(ts_used)},
                    )

                # Allow dev override for regression/smoke: env > meta > cfg
                try:
                    meta_max = None
                    if isinstance(meta, dict):
                        meta_max = meta.get("max_bidask_age_seconds")
                    env_max = os.getenv("TMF_DEV_MAX_BIDASK_AGE_SECONDS", "").strip()
                    if env_max != "":
                        max_age = float(env_max)
                    elif meta_max is not None:
                        max_age = float(meta_max)
                    else:
                        max_age = float(cfg.max_bidask_age_seconds)
                except Exception:
                    max_age = float(cfg.max_bidask_age_seconds)


                allow_stale = _env_truthy("TMF_DEV_ALLOW_STALE_BIDASK", "0")
                # HARDGUARD: Never allow stale override during session.
                # This prevents accidental in-session trading with stale quotes.
                if allow_stale and _in_session(cfg):
                    allow_stale = False
                    # (optional) could log; keep engine pure and let caller print env warnings.
                if age > float(max_age):
                    if allow_stale:
                        return SafetyVerdictV1(
                            True,
                            "OK_DEV_ALLOW_STALE",
                            f"bidask feed stale but allowed by TMF_DEV_ALLOW_STALE_BIDASK=1: age_sec={age:.1f} > max={max_age}",
                            {
                                "bidask_event_id": event_id,
                                "bidask_ts": ts,
                                "age_seconds": age,
                                "max_bidask_age_seconds": float(max_age),
                                "ts_used": str(ts_used),
                                "fop_code": cfg.fop_code,
                                "dev_allow_stale": 1,
                            },
                        )
                    return SafetyVerdictV1(
                        False,
                        "SAFETY_FEED_STALE",
                        f"bidask feed stale: age_sec={age:.1f} > max={max_age}",
                        {
                            "bidask_event_id": event_id,
                            "bidask_ts": ts,
                            "age_seconds": age,
                            "max_bidask_age_seconds": float(max_age),
                                "ts_used": str(ts_used),
                            "fop_code": cfg.fop_code,
                        },
                    )
    
            return SafetyVerdictV1(True, "OK", "system safety pre-trade pass", {"cfg": asdict(cfg)})
