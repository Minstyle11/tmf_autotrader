#!/usr/bin/env bash
set -euo pipefail
PROJ="$HOME/tmf_autotrader"
cd "$PROJ"

# 1) Prompt for API_KEY/SECRET_KEY safely
umask 077
read -r -p "Enter SHIOAJI_API_KEY (visible): " APIK
read -r -s -p "Enter SHIOAJI_SECRET_KEY (hidden): " SECK; echo

cat > configs/secrets/shioaji.env <<EOF
# Shioaji >= 1.0 uses token login (api_key + secret_key). See official docs.
SHIOAJI_API_KEY=$APIK
SHIOAJI_SECRET_KEY=$SECK

# Backward-compat (only for very old shioaji < 1.0; usually unused)
SHIOAJI_PERSON_ID=
SHIOAJI_PASSWORD=
EOF
chmod 600 configs/secrets/shioaji.env
echo "=== [OK] wrote configs/secrets/shioaji.env (chmod 600) ==="

# 2) Patch recorder to prefer token login
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

    # Shioaji >= 1.0 token login (preferred)
    api_key = os.getenv("SHIOAJI_API_KEY", "").strip() or os.getenv("API_KEY", "").strip()
    secret_key = os.getenv("SHIOAJI_SECRET_KEY", "").strip() or os.getenv("SECRET_KEY", "").strip()

    # Legacy (<1.0) fallback (usually unused)
    pid = os.getenv("SHIOAJI_PERSON_ID", "").strip()
    pwd = os.getenv("SHIOAJI_PASSWORD", "").strip()

    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    instruments = cfg.get("instruments", {})
    watch_stocks = cfg.get("watch_stocks", [])

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"raw_events_{stamp}.jsonl"

    api = sj.Shioaji()

    print("[INFO] logging in ...")
    if api_key and secret_key:
        api.login(api_key=api_key, secret_key=secret_key, subscribe_trade=True)
    elif pid and pwd:
        api.login(person_id=pid, passwd=pwd, subscribe_trade=True)
    else:
        die("Missing credentials. Set SHIOAJI_API_KEY & SHIOAJI_SECRET_KEY in configs/secrets/shioaji.env")

    def sub_fut(sym: str):
        try:
            contract = getattr(api.Contracts.Futures, sym)
        except Exception:
            die(f"cannot resolve futures symbol in Contracts.Futures: {sym}")
        api.quote.subscribe(contract, quote_type=sj.constant.QuoteType.Tick, version=sj.constant.QuoteVersion.v1)
        api.quote.subscribe(contract, quote_type=sj.constant.QuoteType.BidAsk, version=sj.constant.QuoteVersion.v1)
        print(f"[OK] subscribed futures {sym}")

    def sub_stk(code: str):
        try:
            c = api.Contracts.Stocks[str(code)]
        except Exception:
            die(f"cannot resolve stock code in Contracts.Stocks: {code}")
        api.quote.subscribe(c, quote_type=sj.constant.QuoteType.Tick, version=sj.constant.QuoteVersion.v1)
        api.quote.subscribe(c, quote_type=sj.constant.QuoteType.BidAsk, version=sj.constant.QuoteVersion.v1)
        print(f"[OK] subscribed stock {code}")

    for sym in ("MTX", "TX", "TMF"):
        if sym in instruments:
            sub_fut(instruments[sym]["symbol"])

    for code in watch_stocks:
        sub_stk(code)

    def write_event(kind: str, payload):
        rec = {
            "ts": datetime.now().isoformat(timespec="milliseconds"),
            "kind": kind,
            "payload": payload if isinstance(payload, dict) else getattr(payload, "__dict__", str(payload)),
        }
        with out_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

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

# 3) Try run immediately (uses existing venv)
echo "=== [RUN] recorder now ==="
. .venv/bin/activate
python -u src/broker/shioaji_recorder.py
