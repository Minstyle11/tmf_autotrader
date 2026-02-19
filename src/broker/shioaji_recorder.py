#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Shioaji recorder (TMF AutoTrader)
- Logs session lifecycle + quote stream events to JSONL under runtime/raw_events/
- Goal: make futures bidask/tick a REAL truth-source for SystemSafety/MarketMetrics.
"""

import os, json, time


def _tmf_json_default(o):
    # Make Shioaji payload JSON-safe (datetime/date -> ISO string)
    try:
        import datetime as _dt
        if isinstance(o, (_dt.datetime, _dt.date)):
            return o.isoformat()
    except Exception:
        pass
    # bytes -> decode best-effort
    if isinstance(o, (bytes, bytearray)):
        try:
            return o.decode("utf-8", errors="replace")
        except Exception:
            return str(o)
    # Path-like -> str
    try:
        from pathlib import Path as _Path
        if isinstance(o, _Path):
            return str(o)
    except Exception:
        pass
    return str(o)


def _tmf_pick_txf_contract(api, wanted_code: str):
    """
    Pick a TXF futures contract.
    - First try direct match by code within api.Contracts.Futures.TXF
    - If missing: fallback to TXFR1/TXFR2 if present
    - Final fallback: choose near-month by delivery_date excluding R1/R2 (per Shioaji official example)
    """
    wanted_code = (wanted_code or "").strip()
    txf = getattr(getattr(getattr(api, "Contracts", None), "Futures", None), "TXF", None)
    if not txf:
        return None

    # direct hit
    try:
        c = txf.get(wanted_code)
        if c is not None:
            return c
    except Exception:
        pass

    # common fallback: near-month alias
    for k in ("TXFR1", "TXFR2"):
        try:
            c = txf.get(k)
            if c is not None:
                return c
        except Exception:
            pass

    # final: pick by delivery_date excluding R1/R2
    try:
        xs = [x for x in txf if getattr(x, "code", "")[-2:] not in ("R1", "R2")]
        if xs:
            return min(xs, key=lambda x: getattr(x, "delivery_date", "9999-99-99"))
    except Exception:
        pass
    return None

from pathlib import Path
from datetime import datetime, timezone

def _tmf_normalize_secret_key32(secret_b64: str) -> str:
    """
    Shioaji expects SECRET_KEY to be base64 for a 32-byte seed (nacl SigningKey seed).
    Some environments provide a 44-char base64 that decodes to 33 bytes (no padding).
    We normalize: if decoded_len==33 -> drop first byte (default) and re-encode to base64 (with padding).
    NOTE: This preserves deterministic behavior and avoids leaking secrets (no prints).
    """
    import base64, binascii
    s = (secret_b64 or "").strip()
    if not s:
        return s
    # tolerate missing padding
    pad = "=" * ((4 - (len(s) % 4)) % 4)
    s2 = s + pad
    try:
        raw = base64.b64decode(s2, validate=True)
    except Exception:
        # if validate fails, try non-validate decode (still no prints)
        raw = base64.b64decode(s2)
    if len(raw) == 32:
        return base64.b64encode(raw).decode("ascii")
    if len(raw) == 33:
        raw32 = raw[1:]  # drop_first (default)
        return base64.b64encode(raw32).decode("ascii")
    # unexpected length -> keep original (caller may raise)
    return s

import shioaji as sj


def _now_iso() -> str:
    # Keep ms precision; UTC ISO
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _safe_to_dict(x):
    # best-effort serializer for shioaji tick/bidask objects
    for attr in ("to_dict", "_asdict", "asdict"):
        fn = getattr(x, attr, None)
        if callable(fn):
            try:
                return fn()
            except Exception:
                pass
    # fallback: dict of public attrs
    try:
        d = {k: getattr(x, k) for k in dir(x) if not k.startswith("_")}
        # strip callables
        d = {k: v for k, v in d.items() if not callable(v)}
        return d
    except Exception:
        return {"repr": repr(x)}



# ---- DB dual-write (M3: REAL market data -> DB -> MarketMetrics) ----
# OFFICIAL intent:
# - Keep raw_events JSONL as truth-source.
# - Also write selected events into sqlite events(kind='bidask_fop_v1'/'tick_fop_v1') for in-session PaperLive.
#
# Controls:
#   TMF_RECORDER_WRITE_DB=1 (default 1)
#   TMF_RECORDER_DB_PATH=runtime/data/tmf_autotrader_v1.sqlite3
#   TMF_RECORDER_DB_COMMIT_EVERY_N=50
#   TMF_RECORDER_DB_COMMIT_EVERY_SEC=1.0
#
# Safety:
# - Creates minimal 'events' table if missing (IF NOT EXISTS).
# - Never raises on DB failure; logs session_error to JSONL instead (best-effort).
def _tmf_db_dual_write_enabled() -> bool:
    import os
    return (os.environ.get("TMF_RECORDER_WRITE_DB", "1").strip() == "1")

class _TmfDbDualWriter:
    def __init__(self):
        self._con = None
        self._n = 0
        self._last_commit_ts = 0.0

    def _ensure(self, db_path: str):
        import sqlite3
        if self._con is not None:
            return
        self._con = sqlite3.connect(db_path)
        self._con.execute("PRAGMA journal_mode=WAL;")
        self._con.execute("""
            CREATE TABLE IF NOT EXISTS events(
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              ts TEXT NOT NULL,
              kind TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              source_file TEXT,
              ingest_ts TEXT
            )
        """)
        self._con.commit()

    def write(self, *, ts: str, kind: str, payload: dict):
        import os, json, time
        if not _tmf_db_dual_write_enabled():
            return
        # Only write market-truth feeds that PaperLive/Safety/MarketMetrics consume.
        if kind not in ("bidask_fop_v1", "tick_fop_v1"):
            return
        db_path = (os.environ.get("TMF_RECORDER_DB_PATH") or "runtime/data/tmf_autotrader_v1.sqlite3").strip()
        commit_n = int((os.environ.get("TMF_RECORDER_DB_COMMIT_EVERY_N", "50") or "50").strip())
        commit_sec = float((os.environ.get("TMF_RECORDER_DB_COMMIT_EVERY_SEC", "1.0") or "1.0").strip())
        self._ensure(db_path)

        source_file = payload.get("source_file")
        ingest_ts = payload.get("ingest_ts") or ts
        self._con.execute(
            "INSERT INTO events(ts, kind, payload_json, source_file, ingest_ts) VALUES (?,?,?,?,?)",
            (ts, kind, json.dumps(payload, ensure_ascii=False, separators=(",",":")), source_file, ingest_ts),
        )
        self._n += 1
        now = time.time()
        if self._n >= commit_n or (now - self._last_commit_ts) >= commit_sec:
            self._con.commit()
            self._n = 0
            self._last_commit_ts = now

    def close(self):
        try:
            if self._con is not None:
                self._con.commit()
                self._con.close()
        finally:
            self._con = None

_tmf_db_writer = _TmfDbDualWriter()
import atexit
atexit.register(_tmf_db_writer.close)

# ---- /DB dual-write ----
def _write_event(fp, kind: str, payload: dict) -> None:
    ts = _now_iso()
    rec = {"ts": ts, "kind": kind, "payload": payload}
    fp.write(json.dumps(rec, ensure_ascii=False, default=_tmf_json_default) + "\n")
    fp.flush()
    # Best-effort: dual-write to sqlite for PaperLive/Safety/MarketMetrics
    try:
        _tmf_db_writer.write(ts=ts, kind=kind, payload=payload)
    except Exception as e:
        # Do NOT crash recorder; record error into JSONL
        try:
            fp.write(json.dumps({"ts": _now_iso(), "kind": "session_error", "payload": {"error": f"db_dual_write_failed: {type(e).__name__}: {e}"}}) + "\n")
            fp.flush()
        except Exception:
            pass


def main() -> int:
    project_root = Path(os.getenv("TMF_PROJECT_ROOT", str(Path.cwd()))).resolve()
    out_dir = project_root / "runtime" / "raw_events"
    _ensure_dir(out_dir)
    out_file = out_dir / f"shioaji_recorder.{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"

    simulation = (os.getenv("TMF_SHIOAJI_SIMULATION", "0").strip() == "1")

    api = sj.Shioaji(simulation=simulation)

    # env keys (do NOT print secrets)
    api_key = (os.getenv("TMF_SHIOAJI_API_KEY") or os.getenv("API_KEY") or os.getenv("SHIOAJI_API_KEY") or "").strip()
    secret  = (os.getenv("TMF_SHIOAJI_SECRET_KEY") or os.getenv("SECRET_KEY") or os.getenv("SHIOAJI_SECRET_KEY") or "").strip()
    secret_raw = secret
    secret_norm = _tmf_normalize_secret_key32(secret_raw)
    secret = secret_norm

    pid     = (os.getenv("TMF_SHIOAJI_PERSON_ID") or os.getenv("PERSON_ID") or os.getenv("SHIOAJI_PERSON_ID") or "").strip()
    pw      = (os.getenv("TMF_SHIOAJI_PASSWORD") or os.getenv("PASSWORD") or os.getenv("SHIOAJI_PASSWORD") or "").strip()

    # futures contract code
    # QuickStart uses TXFC0; you can override (e.g. MXFC0)
    fop_contract_code = os.getenv("TMF_SHIOAJI_FOP_CONTRACT_CODE", "TXFR1").strip()
    # Alias code written into payload['code'] (decouple subscribe contract code vs internal FOP code)
    logical_fop_code = (os.getenv("TMF_FOP_CODE", "TMFB6") or "TMFB6").strip() or "TMFB6"

    want_bidask = (os.getenv("TMF_SHIOAJI_SUB_BIDASK", "1").strip() == "1")
    want_tick   = (os.getenv("TMF_SHIOAJI_SUB_TICK", "1").strip() == "1")

    # recorder options
    run_seconds = int(os.getenv("TMF_SHIOAJI_RUN_SECONDS", "30"))
    source_tag = os.getenv("TMF_SOURCE_FILE", "shioaji_recorder").strip() or "shioaji_recorder"

    with out_file.open("w", encoding="utf-8") as fp:
        _write_event(fp, "session_start", {"msg": "start", "cwd": str(project_root)})

        # callbacks (v1)
        def _on_bidask_fop_v1(*args):
            exchange = args[0] if len(args) > 1 else None
            bidask = args[-1]
            d = _safe_to_dict(bidask)
            # normalize required truth-source fields (best-effort)
            code = d.get("code") or getattr(bidask, "code", None) or fop_contract_code
            bid_p = d.get("bid_price") or getattr(bidask, "bid_price", None)
            ask_p = d.get("ask_price") or getattr(bidask, "ask_price", None)
            bid_v = d.get("bid_volume") or getattr(bidask, "bid_volume", None)
            ask_v = d.get("ask_volume") or getattr(bidask, "ask_volume", None)

            payload = dict(d)
            payload.update({
                "code": logical_fop_code, 'raw_code': code,
                "bid_price": list(bid_p) if bid_p is not None else [],
                "ask_price": list(ask_p) if ask_p is not None else [],
                "bid_volume": list(bid_v) if bid_v is not None else [],
                "ask_volume": list(ask_v) if ask_v is not None else [],
                "synthetic": False,
                "source_file": source_tag,
                "ingest_ts": _now_iso(),
            })
            _write_event(fp, "bidask_fop_v1", payload)

        def _on_tick_fop_v1(*args):
            exchange = args[0] if len(args) > 1 else None
            tick = args[-1]
            d = _safe_to_dict(tick)
            code = d.get("code") or getattr(tick, "code", None) or fop_contract_code
            payload = dict(d)
            payload.update({
                "code": logical_fop_code, 'raw_code': code,
                "synthetic": False,
                "source_file": source_tag,
                "ingest_ts": _now_iso(),
            })
            _write_event(fp, "tick_fop_v1", payload)

        # bind quote callbacks (OFFICIAL: use api.quote.set_on_*_callback for futures stream)
        try:
            api.quote.set_on_bidask_fop_v1_callback(_on_bidask_fop_v1)
            api.quote.set_on_tick_fop_v1_callback(_on_tick_fop_v1)
        except Exception as e:
            _write_event(fp, "session_error", {"error": f"bind_callbacks_failed: {type(e).__name__}: {e}"})
            return 3

        # login
        try:
            if api_key and secret:
                try:
                    # v18/v18.1: unless research-only sandbox, MUST subscribe_trade=True (truth-source)
                    subscribe_trade = (str(os.environ.get("TMF_RESEARCH_ONLY", "0")).strip() != "1")
                    api.login(api_key=api_key, secret_key=secret_raw, subscribe_trade=subscribe_trade)
                except Exception:
                    api.login(api_key=api_key, secret_key=secret_norm, subscribe_trade=subscribe_trade)

                _write_event(fp, "session_ready", {"msg": "login_ok", "simulation": simulation})
            elif pid and pw:
                api.login(person_id=pid, passwd=pw, subscribe_trade=subscribe_trade)
                _write_event(fp, "session_ready", {"msg": "login_ok_pidpw", "simulation": simulation})
            else:
                _write_event(fp, "session_ready", {"msg": "login_skipped_missing_env", "simulation": simulation})
                return 0
        except Exception as e:
            _write_event(fp, "session_error", {"error": f"login_failed: {type(e).__name__}: {e}"})
            return 2

        # subscribe futures
        try:
            c = _tmf_pick_txf_contract(api, fop_contract_code)
            if c is None:
                raise RuntimeError(f"contract_not_found: wanted={fop_contract_code} (try TMF_SHIOAJI_FOP_CONTRACT_CODE=TXFR1)")
        except Exception as e:
            _write_event(fp, "session_error", {"error": f"bad_fop_contract_code={fop_contract_code}: {type(e).__name__}: {e}"})
            return 3

        try:
            if want_tick:
                api.quote.subscribe(c, quote_type=sj.constant.QuoteType.Tick, version=sj.constant.QuoteVersion.v1)
            if want_bidask:
                api.quote.subscribe(c, quote_type=sj.constant.QuoteType.BidAsk, version=sj.constant.QuoteVersion.v1)
            _write_event(fp, "subscribe_ok", {"code": fop_contract_code, "tick": int(want_tick), "bidask": int(want_bidask)})
        except Exception as e:
            _write_event(fp, "session_error", {"error": f"subscribe_failed: {type(e).__name__}: {e}"})
            return 4

        # run window
        t0 = time.time()
        while time.time() - t0 < run_seconds:
            time.sleep(0.2)

        _write_event(fp, "session_stop", {"msg": "stop"})
    print(f"[OK] recorder wrote: {out_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
