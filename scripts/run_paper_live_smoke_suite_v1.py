
from __future__ import annotations


# === TMF_SINGLE_INSTANCE_LOCK_V1_BEGIN ===
def _tmf_single_instance_lock_v1() -> None:
    """
    Prevent overlapping runs (launchd can spawn again before prior run exits).
    Atomic lock via mkdir.
    """
    import os, atexit, time
    lock_dir = os.path.join("runtime", "locks")
    os.makedirs(lock_dir, exist_ok=True)
    lock_path = os.path.join(lock_dir, "paper_smoke_suite_v1.lock")

    try:
        os.mkdir(lock_path)  # atomic
    except FileExistsError:
        print(f"[SKIP] single-instance lock active: {lock_path}")
        raise SystemExit(0)

    # write minimal metadata
    try:
        with open(os.path.join(lock_path, "meta.txt"), "w", encoding="utf-8") as f:
            f.write(f"pid={os.getpid()}\n")
            f.write(f"ts={time.strftime('%Y-%m-%dT%H:%M:%S')}\n")
    except Exception:
        pass

    def _cleanup():
        try:
            # best-effort remove
            meta = os.path.join(lock_path, "meta.txt")
            if os.path.exists(meta):
                os.remove(meta)
            os.rmdir(lock_path)
        except Exception:
            pass

    atexit.register(_cleanup)
# === TMF_SINGLE_INSTANCE_LOCK_V1_END ===

# === TMF_PATCH_HEALTHCHECKS_V2_BEGIN ===
# Persist smoke suite result into LIVE DB (runtime/data/tmf_autotrader_v1.sqlite3), not db_copy.
# Also guarantee persistence via try/finally around main execution.
import os as _os, sqlite3 as _sqlite3, json as _json
from datetime import datetime as _dt

def _tmf_live_db_path() -> str:
    # Always write to live DB unless explicitly overridden.
    return _os.environ.get("TMF_DB_PATH", "runtime/data/tmf_autotrader_v1.sqlite3")

def _tmf_persist_health_checks_v2(*, status: str, summary: dict) -> None:
    db = _tmf_live_db_path()
    con = _sqlite3.connect(db)
    try:
        con.execute(
            "CREATE TABLE IF NOT EXISTS health_checks("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "ts TEXT NOT NULL,"
            "check_name TEXT NOT NULL,"
            "kind TEXT NOT NULL,"
            "status TEXT NOT NULL,"
            "summary_json TEXT NOT NULL"
            ")"
        )
        ts = _dt.now().isoformat(timespec="seconds")
        con.execute(
            "INSERT INTO health_checks(ts, check_name, kind, status, summary_json) VALUES(?,?,?,?,?)",
            (ts, "paper_smoke_suite_v1", "paper_smoke_suite_v1", status, _json.dumps(summary, ensure_ascii=False)),
        )
        con.commit()
        print(f"[OK] health_checks persisted(v2) -> db={db} status={status}")
    finally:
        try:
            con.close()
        except Exception:
            pass
# === TMF_PATCH_HEALTHCHECKS_V2_END ===

import os, json, re, sqlite3, shutil, subprocess, sys, tempfile
from src.data.store_sqlite_v1 import init_db
from pathlib import Path
from datetime import datetime

def _clear_cooldown(con: sqlite3.Connection) -> None:
    con.execute("CREATE TABLE IF NOT EXISTS safety_state(key TEXT PRIMARY KEY, value_json TEXT, ts TEXT)")
    con.execute(
        "INSERT INTO safety_state(key, value_json, ts) VALUES(?,?,datetime('now')) "
        "ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json, ts=excluded.ts",
        ("cooldown", json.dumps({"until_epoch": 0}, ensure_ascii=False)),
    )

def _ensure_index(con: sqlite3.Connection) -> None:
    con.execute("CREATE INDEX IF NOT EXISTS idx_events_kind_ts ON events(kind, ts)")

def _run(env: dict, args: list[str]) -> tuple[int, str]:
    p = subprocess.Popen(args, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    out = p.communicate()[0]
    return p.returncode, out

def _extract(observed: str, key: str) -> str | None:
    m = re.search(rf"{re.escape(key)}\\s*=\\s*([A-Z0-9_]+)", observed)
    return m.group(1) if m else None


# [TMF_AUTO] persist smoke result to main DB (health_checks)
def _persist_smoke_healthcheck_v1(repo: Path, out_log: Path, err_log: Path) -> None:
    import json, re, sqlite3
    from datetime import datetime

    db = repo / "runtime" / "data" / "tmf_autotrader_v1.sqlite3"
    ts = datetime.now().isoformat(timespec="seconds")
    t = ""
    try:
        t = out_log.read_text(encoding="utf-8", errors="replace")
    except Exception:
        t = ""

    m = re.search(r"=== \[SMOKE_SUITE\] db_copy=(.+?) ===\s*", t)
    db_copy = m.group(1).strip() if m else ""
    status = "PASS" if "=== [PASS] smoke suite v1 OK ===" in t else "FAIL"

    obs = {
        "A_has_SAFETY_FEED_STALE": ("SAFETY_FEED_STALE" in t and "=== [A]" in t),
        "B_has_RISK_STOP_REQUIRED": ("RISK_STOP_REQUIRED" in t and "=== [B]" in t),
        "db_copy": db_copy,
    }

    con = sqlite3.connect(str(db))
    try:
        con.execute("PRAGMA foreign_keys=ON")
        con.execute(
            "CREATE TABLE IF NOT EXISTS health_checks ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT,"
            "ts TEXT NOT NULL,"
            "check_name TEXT NOT NULL,"
            "kind TEXT NOT NULL,"
            "status TEXT NOT NULL,"
            "summary_json TEXT NOT NULL,"
            "out_log TEXT,"
            "err_log TEXT,"
            "meta_json TEXT"
            ")"
        )
        con.execute("CREATE INDEX IF NOT EXISTS idx_health_checks_name_ts ON health_checks(check_name, ts)")
        con.execute(
            "INSERT INTO health_checks(ts, check_name, kind, status, summary_json, out_log, err_log, meta_json) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (
                ts,
                "paper_smoke_suite_v1",
                "paper_smoke_suite_v1",
                status,
                json.dumps(obs, ensure_ascii=False),
                str(out_log),
                str(err_log),
                json.dumps({"db_path": str(db), "db_copy": db_copy}, ensure_ascii=False),
            )
        )
        con.commit()
        print(f"[OK] health_checks persisted: status={status} ts={ts}")
    finally:
        try:
            con.close()
        except Exception:
            pass


def main():
    repo = Path.cwd()
    db_src = Path(os.environ.get("TMF_DB_PATH", str(repo / "runtime" / "data" / "tmf_autotrader_v1.sqlite3")))
    if not db_src.exists():
        raise SystemExit(f"[FATAL] missing db: {db_src}")

    tmpdir = Path(tempfile.mkdtemp(prefix="tmf_smoke_"))
    db = tmpdir / "tmf_autotrader_smoke.sqlite3"
    shutil.copy2(db_src, db)

    # idempotent schema init (db_copy may come from an uninitialized source)
    init_db(db)

    con = sqlite3.connect(str(db))
    try:
        con.execute("PRAGMA foreign_keys=ON;")
        _clear_cooldown(con)
        _ensure_index(con)
        con.commit()
    finally:
        con.close()

    print(f"=== [SMOKE_SUITE] db_copy={db} ===")
    print("=== [A] strict expect SAFETY_FEED_STALE ===")
    envA = os.environ.copy()
    envA.update({
        "PYTHONPATH": str(repo),
        "TMF_DB_PATH": str(db),
        "TMF_FOP_CODE": envA.get("TMF_FOP_CODE","TMFB6"),
        "TMF_MAX_BIDASK_AGE_SECONDS": "15",
        "TMF_DEV_ALLOW_STALE_BIDASK": "0",
    })
    rcA, outA = _run(envA, [sys.executable, "src/oms/run_paper_live_v1.py", "--db", str(db)])
    print(outA)

    okA = ("SAFETY_FEED_STALE" in outA) and ("smoke_ok = True" in outA)
    if not okA:
        print("[FAIL] A did not observe SAFETY_FEED_STALE")
        raise SystemExit(2)

    # clear cooldown again inside db copy
    con = sqlite3.connect(str(db))
    try:
        _clear_cooldown(con)
        con.commit()
    finally:
        con.close()

    print("=== [B] offline allow-stale expect RISK_STOP_REQUIRED ===")
    envB = os.environ.copy()
    envB.update({
        "PYTHONPATH": str(repo),
        "TMF_DB_PATH": str(db),
        "TMF_FOP_CODE": envB.get("TMF_FOP_CODE","TMFB6"),
        "TMF_MAX_BIDASK_AGE_SECONDS": "86400",
        "TMF_DEV_ALLOW_STALE_BIDASK": "1",
    })
    rcB, outB = _run(envB, [sys.executable, "src/oms/run_paper_live_v1.py", "--db", str(db)])
    print(outB)

    okB = ("RISK_STOP_REQUIRED" in outB) and ("case1_expected_reject_code = RISK_STOP_REQUIRED ok= True" in outB)
    if not okB:
        print("[FAIL] B did not observe RISK_STOP_REQUIRED")
        raise SystemExit(3)

    print("=== [PASS] smoke suite v1 OK ===")
    return 0

# _TMF_MAIN_WRAPPED_V2

if __name__ == "__main__":
    _tmf_single_instance_lock_v1()
    _tmf_hc_status = "PASS"
    _tmf_hc_summary = {}
    try:
        if "main" in globals() and callable(globals()["main"]):
            _rc = globals()["main"]()
            if isinstance(_rc, int) and _rc != 0:
                _tmf_hc_status = "FAIL"
                _tmf_hc_summary["exit_code"] = _rc
        elif "run" in globals() and callable(globals()["run"]):
            _rc = globals()["run"]()
            if isinstance(_rc, int) and _rc != 0:
                _tmf_hc_status = "FAIL"
                _tmf_hc_summary["exit_code"] = _rc
        else:
            # Fall back: if the script's logic is top-level, we can't "call" it here.
            # Mark as FAIL so we don't emit false PASS without executing suite logic.
            _tmf_hc_status = "FAIL"
            _tmf_hc_summary["reason"] = "no main()/run() callable found; __main__ wrapper replaced old entrypoint"
    except SystemExit as _e:
        _code = getattr(_e, "code", 1)
        if _code not in (0, None):
            _tmf_hc_status = "FAIL"
            _tmf_hc_summary["system_exit_code"] = _code
        raise
    except Exception as _e:
        _tmf_hc_status = "FAIL"
        _tmf_hc_summary["exc"] = repr(_e)
        raise
    finally:
        try:
            _tmf_persist_health_checks_v2(status=_tmf_hc_status, summary=_tmf_hc_summary)
        except Exception as _e2:
            print("[WARN] health_checks persist failed:", repr(_e2))
