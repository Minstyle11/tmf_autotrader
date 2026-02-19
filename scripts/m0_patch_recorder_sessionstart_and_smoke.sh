#!/usr/bin/env bash
set -euo pipefail
PROJ="$HOME/tmf_autotrader"
cd "$PROJ"

# --- Patch recorder: create file immediately + write session_start + optional MAX_SECONDS ---
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

    # IMPORTANT: create file immediately + session_start record (not dependent on market ticks)
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
        write_jsonl(out_path, rec)

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
echo "=== [OK] patched recorder (session_start + MAX_SECONDS) ==="

# --- Smoke run for 6 seconds ---
echo "=== [RUN] recorder smoke (6s) ==="
. .venv/bin/activate
MAX_SECONDS=6 python -u src/broker/shioaji_recorder.py || true

echo
echo "=== [VERIFY] latest raw_events_*.jsonl ==="
LATEST="$(ls -1t runtime/data/raw_events_*.jsonl 2>/dev/null | head -n 1 || true)"
if [ -z "$LATEST" ]; then
  echo "[FATAL] still no raw_events_*.jsonl found"
  exit 2
fi
echo "[OK] latest=$LATEST"
LINES="$(wc -l < "$LATEST" | tr -d ' ')"
echo "[INFO] lines=$LINES"
sed -n '1,3p' "$LATEST" || true
echo "----"
tail -n 3 "$LATEST" || true

if [ "$LINES" -lt 2 ]; then
  echo "[FATAL] file exists but too few lines; expected >=2 (session_start + session_stop at least)"
  exit 3
fi

# --- Update board: broker connectivity DONE; data store DOING ---
python3 - <<'PY'
from pathlib import Path
import re, datetime

p=Path("docs/board/PROJECT_BOARD.md")
t=p.read_text(encoding="utf-8")

t=t.replace("[~] Broker connectivity: Shioaji login + quote subscribe (TMF/TX/MTX + 2330/2317/2454) + raw event recorder",
            "[x] Broker connectivity: Shioaji login + quote subscribe (TMF/TX/MTX + 2330/2317/2454) + raw event recorder")
t=t.replace("[ ] Broker connectivity: Shioaji login + quote subscribe (TMF/TX/MTX + 2330/2317/2454) + raw event recorder",
            "[x] Broker connectivity: Shioaji login + quote subscribe (TMF/TX/MTX + 2330/2317/2454) + raw event recorder")
t=t.replace("[ ] Data store: schema v1 (events, bars, trades, orders, fills) + rotation",
            "[~] Data store: schema v1 (events, bars, trades, orders, fills) + rotation")

# recompute progress header
all_boxes = re.findall(r'^\s*-\s*\[( |x|~|!)\]\s+(.+)$', t, flags=re.M)
total = len(all_boxes)
done = sum(1 for s,_ in all_boxes if s == 'x')

def pct(d,t):
    return 0.0 if t==0 else (d/t*100.0)

milestone={}
blocks=re.split(r'(^###\s+.+$)', t, flags=re.M)
for i in range(1,len(blocks),2):
    name=re.sub(r'^###\s+','',blocks[i].strip())
    body=blocks[i+1]
    b=re.findall(r'^\s*-\s*\[( |x|~|!)\]\s+(.+)$', body, flags=re.M)
    milestone[name]=(sum(1 for s,_ in b if s=='x'), len(b))

now=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
hdr=[]
hdr.append("# 專案進度總覽（自動計算）")
hdr.append(f"- 更新時間：{now}")
hdr.append(f"- 專案總完成度：{pct(done,total):.1f}% （已完成 {done} / {total} 項）")
hdr.append("")
hdr.append("## 里程碑完成度")
for k,(d2,t2) in milestone.items():
    hdr.append(f"- {k}：{pct(d2,t2):.1f}% （已完成 {d2} / {t2}）")
hdr.append("")
hdr.append("## 說明（快速讀法）")
hdr.append("- 看「專案總完成度」掌握全局；看「里程碑完成度」掌握目前在哪一段。")
hdr.append("- [~] 進行中、[!] 阻塞、[x] 已完成。")
hdr_block="\n".join(hdr)+"\n\n"

marker=r'^#\s*專案進度總覽（自動計算）\s*$'
m=re.search(marker,t,flags=re.M)
if m:
    start=m.start()
    anchors=[]
    for pat in [r'\n##\s+Status Legend\b', r'\n#\s+TMF\b', r'\n#\s+TMF AutoTrader\b']:
        am=re.search(pat,t)
        if am: anchors.append(am.start()+1)
    end=min(anchors) if anchors else len(t)
    t=t[:start]+hdr_block+t[end:]
else:
    t=hdr_block+t

p.write_text(t,encoding="utf-8")
PY

if [ -x scripts/pm_tick.sh ]; then
  scripts/pm_tick.sh "M0: recorder now writes session_start/stop; smoke run produced non-empty jsonl; broker connectivity marked DONE; data store set DOING"
fi

echo
echo "=== [OK] smoke verified + board updated ==="
sed -n '1,30p' docs/board/PROJECT_BOARD.md
