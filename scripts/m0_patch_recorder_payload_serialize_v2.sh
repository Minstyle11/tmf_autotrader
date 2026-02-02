#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/tmf_autotrader"

cat > src/broker/shioaji_recorder.py <<'PY'
import os, sys, json, time, signal
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
import yaml
import shioaji as sj

STOP = False

def _sig(*_):
    global STOP
    STOP = True

def die(msg: str, code: int = 2):
    print(f"[FATAL] {msg}", file=sys.stderr)
    sys.exit(code)

def write_jsonl(path: Path, rec: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def is_jsonable(x):
    return isinstance(x, (str, int, float, bool)) or x is None

def obj_to_dict(obj):
    """
    Robust serializer for Shioaji Tick/BidAsk objects (often extension types with empty __dict__).
    Priority:
      1) dict already
      2) to_dict()
      3) _asdict() (namedtuple-like)
      4) vars(obj) if non-empty
      5) dir(obj) -> collect non-callable, non-private, jsonable fields
      6) fallback to str(obj)
    """
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj
    for m in ("to_dict", "_asdict"):
        if hasattr(obj, m) and callable(getattr(obj, m)):
            try:
                d = getattr(obj, m)()
                if isinstance(d, dict) and d:
                    return d
            except Exception:
                pass
    try:
        d = vars(obj)
        if isinstance(d, dict) and d:
            return d
    except Exception:
        pass

    out = {}
    try:
        for name in dir(obj):
            if name.startswith("_"):
                continue
            try:
                v = getattr(obj, name)
            except Exception:
                continue
            if callable(v):
                continue
            if is_jsonable(v):
                out[name] = v
            elif isinstance(v, (list, tuple)) and all(is_jsonable(i) for i in v):
                out[name] = list(v)
            # keep it conservative: do not recurse deep here
        if out:
            return out
    except Exception:
        pass

    return {"_repr": str(obj)}

def main():
    repo = Path(__file__).resolve().parents[2]
    cfg_path = repo / "configs" / "instruments.yaml"
    env_path = repo / "configs" / "secrets" / "shioaji.env"
    out_dir = repo / "runtime" / "data"
    out_dir.mkdir(parents=True, exist_ok=True)

    if not cfg_path.exists():
        die(f"missing config: {cfg_path}")
    if not env_path.exists():
        die(f"missing secrets env: {env_path}")

    load_dotenv(env_path)

    api_key = (os.getenv("SHIOAJI_API_KEY","") or os.getenv("API_KEY","")).strip()
    secret_key = (os.getenv("SHIOAJI_SECRET_KEY","") or os.getenv("SECRET_KEY","")).strip()
    pid = os.getenv("SHIOAJI_PERSON_ID", "").strip()
    pwd = os.getenv("SHIOAJI_PASSWORD", "").strip()

    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    instruments = cfg.get("instruments", {})
    watch_stocks = cfg.get("watch_stocks", [])

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"raw_events_{stamp}.jsonl"

    # create file immediately + session_start record
    write_jsonl(out_path, {
        "ts": datetime.now().isoformat(timespec="milliseconds"),
        "kind": "session_start",
        "payload": {
            "cwd": str(Path.cwd()),
            "out_path": str(out_path),
            "primary": cfg.get("primary"),
            "instruments": {k: {"group": v.get("group"), "key": v.get("key")} for k, v in instruments.items()},
            "watch_stocks": watch_stocks,
        }
    })

    api = sj.Shioaji()

    print("[INFO] logging in (contracts_timeout=15000ms) ...")
    if api_key and secret_key:
        api.login(api_key=api_key, secret_key=secret_key, contracts_timeout=15000)
    elif pid and pwd:
        api.login(person_id=pid, passwd=pwd, contracts_timeout=15000)
    else:
        die("Missing credentials. Set SHIOAJI_API_KEY & SHIOAJI_SECRET_KEY in configs/secrets/shioaji.env")

    def write_event(kind: str, payload_obj):
        payload = obj_to_dict(payload_obj)
        rec = {
            "ts": datetime.now().isoformat(timespec="milliseconds"),
            "kind": kind,
            "payload": payload,
        }
        write_jsonl(out_path, rec)

    # handlers
    @api.on_tick_fop_v1()
    def on_tick_fop(exchange, tick):
        write_event("tick_fop_v1", tick)

    @api.on_bidask_fop_v1()
    def on_ba_fop(exchange, bidask):
        write_event("bidask_fop_v1", bidask)

    @api.on_tick_stk_v1()
    def on_tick_stk(exchange, tick):
        write_event("tick_stk_v1", tick)

    @api.on_bidask_stk_v1()
    def on_ba_stk(exchange, bidask):
        write_event("bidask_stk_v1", bidask)

    # subscribe futures via group+key
    for name, spec in instruments.items():
        if str(spec.get("kind","")).lower() != "futures":
            continue
        group = spec.get("group")
        key = spec.get("key")
        if not group or not key:
            die(f"instrument {name} missing group/key in configs/instruments.yaml")
        try:
            contract = api.Contracts.Futures[group][key]
        except Exception as e:
            die(f"cannot resolve Futures[{group}][{key}]: {e}")
        api.quote.subscribe(contract, quote_type=sj.constant.QuoteType.Tick, version=sj.constant.QuoteVersion.v1)
        api.quote.subscribe(contract, quote_type=sj.constant.QuoteType.BidAsk, version=sj.constant.QuoteVersion.v1)
        print(f"[OK] subscribed futures {name}: {group}/{key} (symbol={getattr(contract,'symbol','')}, name={getattr(contract,'name','')})")

    # subscribe stocks
    for code in watch_stocks:
        code = str(code)
        try:
            c = api.Contracts.Stocks[code]
        except Exception as e:
            die(f"cannot resolve stock code {code}: {e}")
        api.quote.subscribe(c, quote_type=sj.constant.QuoteType.Tick, version=sj.constant.QuoteVersion.v1)
        api.quote.subscribe(c, quote_type=sj.constant.QuoteType.BidAsk, version=sj.constant.QuoteVersion.v1)
        print(f"[OK] subscribed stock {code}")

    write_event("session_ready", {"msg": "subscriptions_sent"})
    max_seconds = float(os.getenv("MAX_SECONDS", "0") or "0")
    t0 = time.time()

    print(f"[RUN] recording -> {out_path}")
    print("[NOTE] MAX_SECONDS=" + str(max_seconds) + " (0 means run forever)")

    while not STOP:
        time.sleep(0.2)
        if max_seconds > 0 and (time.time() - t0) >= max_seconds:
            break

    print("[INFO] stopping ...")
    try:
        api.logout()
    except Exception:
        pass
    write_event("session_stop", {"reason": "signal" if STOP else "max_seconds"})
    print("[OK] stopped")

if __name__ == "__main__":
    signal.signal(signal.SIGINT, _sig)
    signal.signal(signal.SIGTERM, _sig)
    main()
PY

echo "=== [OK] patched recorder serialization v2 ==="

echo "=== [RUN] recorder for 20s ==="
. .venv/bin/activate
MAX_SECONDS=20 python -u src/broker/shioaji_recorder.py || true

echo
echo "=== [INSPECT] latest raw_events_*.jsonl sample keys ==="
LATEST="$(ls -1t runtime/data/raw_events_*.jsonl 2>/dev/null | head -n 1 || true)"
if [ -z "$LATEST" ]; then
  echo "[FATAL] no raw_events file found"
  exit 2
fi
echo "[OK] latest=$LATEST"

python3 - <<'PY'
import json, sys, collections, pathlib
p=pathlib.Path(sys.argv[1])
want={"tick_fop_v1":None,"bidask_fop_v1":None,"tick_stk_v1":None,"bidask_stk_v1":None}
with p.open("r",encoding="utf-8") as f:
    for line in f:
        obj=json.loads(line)
        k=obj.get("kind")
        if k in want and want[k] is None and isinstance(obj.get("payload"), dict):
            want[k]=obj["payload"]
        if all(v is not None for v in want.values()):
            break

for k,v in want.items():
    if v is None:
        print(f"=== {k} ===\n[MISS]\n")
        continue
    keys=sorted(list(v.keys()))
    print(f"=== {k} ===")
    print("[KEYS]", keys[:80])
    if not keys:
        print("[WARN] payload still empty {}")
    print()
PY "$LATEST"
