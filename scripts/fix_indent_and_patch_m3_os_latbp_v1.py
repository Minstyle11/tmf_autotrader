from __future__ import annotations
from pathlib import Path
from datetime import datetime
import glob, os, re, subprocess, textwrap, sys

MARK = "### M3-OS-1 LATENCY_BACKPRESSURE_V1 (AUTO) ###"
NEEDLE_RE = re.compile(r'^(?P<indent>\s*)return\s+SafetyVerdictV1\(True,\s*"OK",\s*"system safety pre-trade pass",\s*\{"cfg":\s*asdict\(cfg\)\}\)\s*$')

def ts():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def backup(p: Path):
    if p.exists():
        b = p.with_suffix(p.suffix + f".bak_fix_{ts()}")
        b.write_bytes(p.read_bytes())
        print(f"[OK] backup -> {b}")

def find_latest_backup(pattern: str) -> Path | None:
    cands = sorted(glob.glob(pattern))
    if not cands:
        return None
    # lexicographic works because timestamp format is YYYYMMDD_HHMMSS
    return Path(cands[-1])

def indent_block(block: str, indent: str) -> str:
    out_lines = []
    for ln in block.splitlines():
        if ln.strip() == "":
            out_lines.append("")
        else:
            out_lines.append(indent + ln)
    return "\n".join(out_lines)

def run(cmd: list[str]):
    r = subprocess.run(cmd, text=True)
    if r.returncode != 0:
        raise SystemExit(f"[FATAL] command failed rc={r.returncode}: {' '.join(cmd)}")

def board_set(task_id: str, want_done: bool):
    b = Path("docs/board/PROJECT_BOARD.md")
    if not b.exists():
        print("[WARN] missing board:", b)
        return
    txt = b.read_text(encoding="utf-8", errors="replace")
    a = f"- [ ] [TASK:{task_id}]"
    x = f"- [x] [TASK:{task_id}]"
    if want_done:
        if a in txt:
            bak = b.with_suffix(b.suffix + f".bak_{ts()}")
            bak.write_text(txt, encoding="utf-8")
            b.write_text(txt.replace(a, x), encoding="utf-8")
            print(f"[OK] board -> DONE {task_id}")
        else:
            print(f"[OK] board unchanged (already DONE or not found): {task_id}")
    else:
        if x in txt:
            bak = b.with_suffix(b.suffix + f".bak_{ts()}")
            bak.write_text(txt, encoding="utf-8")
            b.write_text(txt.replace(x, a), encoding="utf-8")
            print(f"[OK] board -> TODO {task_id}")
        else:
            print(f"[OK] board unchanged (already TODO or not found): {task_id}")

def main():
    task = "M3-OS-1a2f3c4d"
    # Keep evidence chain: revert to TODO before proving PASS
    board_set(task, want_done=False)

    p = Path("src/safety/system_safety_v1.py")
    if not p.exists():
        raise SystemExit(f"[FATAL] missing: {p}")

    # Restore from latest backup made by previous patch step
    bak = find_latest_backup("src/safety/system_safety_v1.py.bak_20260220_103115")
    if bak is None or not bak.exists():
        # fallback: any .bak_ timestamp
        bak = find_latest_backup("src/safety/system_safety_v1.py.bak_*")
    if bak is None or not bak.exists():
        raise SystemExit("[FATAL] cannot find any backup for system_safety_v1.py")

    src = bak.read_text(encoding="utf-8", errors="replace")
    # If already patched in backup, just use it; else patch now with correct indent
    if MARK in src:
        print("[WARN] backup already contains MARK; will still re-generate from backup to fix indentation.")
    # Find the OK return line indent from backup
    m = NEEDLE_RE.search(src)
    if not m:
        raise SystemExit("[FATAL] cannot locate OK return needle in backup (pattern mismatch)")

    base_indent = m.group("indent")

    insert_raw = textwrap.dedent(f"""
{MARK}
# OS guard: latency + backpressure (queue/lag) -> COOLDOWN/KILL
# Deterministic: any internal error -> COOLDOWN (fail-safe)
try:
    from src.ops.latency.latency_budget import LatencyBudgetV1
    from src.ops.latency.backpressure_governor import BackpressureConfigV1, decide as bp_decide

    def _meta_env_int(meta: dict, meta_key: str, env_key: str, default: int) -> int:
        try:
            if isinstance(meta, dict) and meta_key in meta and meta[meta_key] is not None:
                return int(float(meta[meta_key]))
        except Exception:
            pass
        v = os.getenv(env_key, "").strip()
        if v != "":
            try:
                return int(float(v))
            except Exception:
                return default
        return default

    # feed_age_ms: derive from latest bidask's recv_ts/ingest_ts (when available)
    feed_age_ms = 0
    if cfg.require_recent_bidask == 1:
        con = self._con()
        try:
            ev2 = self._latest_event_by_code(
                con,
                kind=cfg.bidask_kind,
                code=cfg.fop_code,
                reject_synthetic=bool(getattr(cfg, "reject_synthetic_bidask", 1)),
            )
        finally:
            con.close()
        if ev2:
            _event_id2, _ts2, _payload2 = ev2
            ts_used2 = None
            if isinstance(_payload2, dict):
                ts_used2 = _payload2.get("recv_ts") or _payload2.get("ingest_ts") or _ts2
            else:
                ts_used2 = _ts2
            age2 = self._age_seconds(str(ts_used2))
            if age2 is not None:
                feed_age_ms = int(float(age2) * 1000.0)

    broker_rtt_ms = 0
    oms_queue_depth = 0
    if isinstance(meta, dict):
        try: broker_rtt_ms = int(meta.get("broker_rtt_ms", 0) or 0)
        except Exception: broker_rtt_ms = 0
        try: oms_queue_depth = int(meta.get("oms_queue_depth", 0) or 0)
        except Exception: oms_queue_depth = 0

    metrics = {{
        "feed_age_ms": int(feed_age_ms),
        "broker_rtt_ms": int(broker_rtt_ms),
        "oms_queue_depth": int(oms_queue_depth),
    }}

    lat = LatencyBudgetV1(
        max_feed_age_ms=_meta_env_int(meta, "tmf_max_feed_age_ms", "TMF_MAX_FEED_AGE_MS", 1500),
        max_broker_rtt_ms=_meta_env_int(meta, "tmf_max_broker_rtt_ms", "TMF_MAX_BROKER_RTT_MS", 1200),
        max_oms_queue_depth=_meta_env_int(meta, "tmf_max_oms_queue_depth", "TMF_MAX_OMS_QUEUE_DEPTH", 50),
    )
    lv = lat.check(metrics)

    bp_cfg = BackpressureConfigV1(
        cooldown_seconds=_meta_env_int(meta, "tmf_backpressure_cooldown_seconds", "TMF_BACKPRESSURE_COOLDOWN_SECONDS", 30),
        kill_on_extreme=_meta_env_int(meta, "tmf_backpressure_kill_on_extreme", "TMF_BACKPRESSURE_KILL_ON_EXTREME", 1),
    )
    bp = bp_decide(metrics, bp_cfg)

    if (not bp.ok) and getattr(bp, "action", "") == "KILL":
        self.request_kill(
            code="BACKPRESSURE_EXTREME",
            reason="backpressure extreme -> kill requested",
            details={{"metrics": metrics, "latency": lv, "bp": bp.__dict__}},
        )
        return SafetyVerdictV1(False, "SAFETY_KILL_SWITCH", "backpressure extreme -> kill-switch enabled", {{"metrics": metrics, "latency": lv, "bp": bp.__dict__}})

    if (not lv.get("ok", True)) or ((not bp.ok) and getattr(bp, "action", "") == "COOLDOWN"):
        cd = int(getattr(bp_cfg, "cooldown_seconds", 30) or 30)
        self.request_cooldown(
            seconds=cd,
            code="LATBP_COOLDOWN",
            reason="latency/backpressure triggered cooldown",
            details={{"metrics": metrics, "latency": lv, "bp": bp.__dict__}},
        )
        return SafetyVerdictV1(False, "SAFETY_COOLDOWN_ACTIVE", "latency/backpressure triggered cooldown", {{"cooldown_seconds": cd, "metrics": metrics, "latency": lv, "bp": bp.__dict__}})

except Exception as _e:
    try:
        self.request_cooldown(seconds=30, code="LATBP_OS_ERROR", reason="latency/backpressure module error", details={{"err": str(_e)}})
    except Exception:
        pass
    return SafetyVerdictV1(False, "SAFETY_COOLDOWN_ACTIVE", "latency/backpressure module error -> cooldown", {{"err": str(_e)}})
""").strip("\n")

    # Build replacement using correct indent
    insert = indent_block(insert_raw, base_indent)

    # Replace ONLY the first occurrence of the needle line
    def repl(match: re.Match) -> str:
        line = match.group(0)
        return insert + "\n\n" + line  # keep original indentation exactly

    src2, n = NEEDLE_RE.subn(repl, src, count=1)
    if n != 1:
        raise SystemExit(f"[FATAL] needle replacement count != 1 (got {n})")

    backup(p)
    p.write_text(src2, encoding="utf-8")
    print("[OK] restored from backup + patched with preserved indent:", p)

    # Compile + regression
    run(["python3", "-c", "import py_compile; py_compile.compile('src/safety/system_safety_v1.py', doraise=True); print('[OK] py_compile PASS')"])
    run(["bash", "scripts/m3_regression_latency_backpressure_v1.sh"])

    # Mark DONE only after PASS
    board_set(task, want_done=True)

    if Path("scripts/pm_refresh_board_and_verify.sh").exists():
        run(["bash", "scripts/pm_refresh_board_and_verify.sh"])
    if Path("scripts/mk_windowpack_ultra.sh").exists():
        run(["bash", "scripts/mk_windowpack_ultra.sh"])

    print("[程序完成]")

if __name__ == "__main__":
    main()
