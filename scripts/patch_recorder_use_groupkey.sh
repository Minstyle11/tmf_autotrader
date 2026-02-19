#!/usr/bin/env bash
set -euo pipefail
PROJ="$HOME/tmf_autotrader"
cd "$PROJ"

# 1) Update instruments.yaml to Shioaji Futures group+key (R1 continuous)
cat > configs/instruments.yaml <<'YAML'
primary: MXF
instruments:
  MXF:
    kind: futures
    group: MXF
    key: MXFR1
    multiplier_twd_per_point: 50
    tick_size: 1
  TXF:
    kind: futures
    group: TXF
    key: TXFR1
    multiplier_twd_per_point: 200
    tick_size: 1
  TMF:
    kind: futures
    group: TMF
    key: TMFR1
    multiplier_twd_per_point: 10
    tick_size: 1
watch_stocks:
  - "2330"
  - "2317"
  - "2454"
YAML
echo "=== [OK] wrote configs/instruments.yaml (group+key) ==="

# 2) Patch recorder to use Futures[group][key]
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

    api = sj.Shioaji()

    print("[INFO] logging in (contracts_timeout=15000ms) ...")
    if api_key and secret_key:
        api.login(api_key=api_key, secret_key=secret_key, contracts_timeout=15000, subscribe_trade=True)
    elif pid and pwd:
        api.login(person_id=pid, passwd=pwd, contracts_timeout=15000, subscribe_trade=True)
    else:
        die("Missing credentials. Set SHIOAJI_API_KEY & SHIOAJI_SECRET_KEY in configs/secrets/shioaji.env")

    def write_event(kind: str, payload):
        rec = {
            "ts": datetime.now().isoformat(timespec="milliseconds"),
            "kind": kind,
            "payload": payload if isinstance(payload, dict) else getattr(payload, "__dict__", str(payload)),
        }
        with out_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # --- Handlers ---
    @api.on_tick_fop_v1()
    def on_tick_fop(exchange, tick):
        write_event("tick_fop_v1", tick.__dict__)

    @api.on_bidask_fop_v1()
    def on_ba_fop(exchange, bidask):
        write_event("bidask_fop_v1", bidask.__dict__)

    @api.on_tick_stk_v1()
    def on_tick_stk(exchange, tick):
        write_event("tick_stk_v1", tick.__dict__)

    @api.on_bidask_stk_v1()
    def on_ba_stk(exchange, bidask):
        write_event("bidask_stk_v1", bidask.__dict__)

    # --- Subscribe futures via group+key ---
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

    # --- Subscribe stocks ---
    for code in watch_stocks:
        code = str(code)
        try:
            c = api.Contracts.Stocks[code]
        except Exception as e:
            die(f"cannot resolve stock code {code}: {e}")
        api.quote.subscribe(c, quote_type=sj.constant.QuoteType.Tick, version=sj.constant.QuoteVersion.v1)
        api.quote.subscribe(c, quote_type=sj.constant.QuoteType.BidAsk, version=sj.constant.QuoteVersion.v1)
        print(f"[OK] subscribed stock {code}")

    print(f"[RUN] recording -> {out_path}")
    print("[NOTE] Press Ctrl+C to stop after you see subscriptions + some events.")
    while not STOP:
        time.sleep(0.2)

    print("[INFO] stopping ...")
    try:
        api.logout()
    except Exception:
        pass
    print("[OK] stopped")

if __name__ == "__main__":
    signal.signal(signal.SIGINT, _sig)
    signal.signal(signal.SIGTERM, _sig)
    main()
PY
echo "=== [OK] patched src/broker/shioaji_recorder.py (group+key subscribe) ==="

# 3) Run recorder now
echo "=== [RUN] recorder now (Ctrl+C after you see [OK] subscribed...) ==="
. .venv/bin/activate
python -u src/broker/shioaji_recorder.py
