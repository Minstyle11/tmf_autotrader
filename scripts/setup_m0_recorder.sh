#!/usr/bin/env bash
set -euo pipefail

PROJ="$HOME/tmf_autotrader"
cd "$PROJ"

# --- venv ---
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
. .venv/bin/activate
python -m pip install -U pip wheel >/dev/null
python -m pip install -U shioaji python-dotenv pyyaml >/dev/null

# --- instruments config (MTX primary; switchable to TX/TMF) ---
cat > configs/instruments.yaml <<'YAML'
primary: MTX
instruments:
  MTX:
    kind: futures
    symbol: MTX
    multiplier_twd_per_point: 50
    tick_size: 1
  TX:
    kind: futures
    symbol: TX
    multiplier_twd_per_point: 200
    tick_size: 1
  TMF:
    kind: futures
    symbol: TMF
    multiplier_twd_per_point: 10
    tick_size: 1
watch_stocks:
  - "2330"
  - "2317"
  - "2454"
YAML

# --- secrets template (YOU fill in) ---
mkdir -p configs/secrets
if [ ! -f configs/secrets/shioaji.env ]; then
  cat > configs/secrets/shioaji.env <<'ENV'
# Fill these with your real credentials (DO NOT COMMIT)
SHIOAJI_PERSON_ID=
SHIOAJI_PASSWORD=
ENV
fi

# --- recorder ---
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

    pid = os.getenv("SHIOAJI_PERSON_ID", "").strip()
    pwd = os.getenv("SHIOAJI_PASSWORD", "").strip()
    if not pid or not pwd:
        die("SHIOAJI_PERSON_ID / SHIOAJI_PASSWORD not set in configs/secrets/shioaji.env")

    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    instruments = cfg.get("instruments", {})
    watch_stocks = cfg.get("watch_stocks", [])

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"raw_events_{stamp}.jsonl"

    api = sj.Shioaji()

    print("[INFO] logging in ...")
    api.login(person_id=pid, passwd=pwd)

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

    # subscribe MTX/TX/TMF if present
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
    print("[NOTE] Press Ctrl+C to stop.")
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

# --- run wrapper ---
cat > scripts/run_recorder.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail
cd "$HOME/tmf_autotrader"
. .venv/bin/activate
python -u src/broker/shioaji_recorder.py
SH
chmod +x scripts/run_recorder.sh

# --- update board status ---
python3 - <<'PY'
from pathlib import Path
p=Path("docs/board/PROJECT_BOARD.md")
t=p.read_text(encoding="utf-8")
t=t.replace("[~] Create repo skeleton + board + bible system + backup framework",
            "[x] Create repo skeleton + board + bible system + backup framework")
t=t.replace("[ ] Broker connectivity: Shioaji login + quote subscribe (TMF/TX/MTX + 2330/2317/2454) + raw event recorder",
            "[~] Broker connectivity: Shioaji login + quote subscribe (TMF/TX/MTX + 2330/2317/2454) + raw event recorder")
p.write_text(t,encoding="utf-8")
PY

# --- tick changelog ---
if [ -x scripts/pm_tick.sh ]; then
  scripts/pm_tick.sh "M0: venv+deps installed; instruments.yaml+recorder created; broker connectivity set DOING"
fi

echo "=== [OK] M0 recorder skeleton ready ==="
echo "NEXT: edit configs/secrets/shioaji.env (fill id/password), then run: ./scripts/run_recorder.sh"
echo "=== [SHOW] secrets template ==="
sed -n '1,40p' configs/secrets/shioaji.env || true
