#!/usr/bin/env bash
set -euo pipefail
PROJ="$HOME/tmf_autotrader"
cd "$PROJ"

echo "=== [1] locate latest raw_events_*.jsonl ==="
LATEST="$(ls -1t runtime/data/raw_events_*.jsonl 2>/dev/null | head -n 1 || true)"
if [ -z "${LATEST}" ]; then
  echo "[FATAL] no runtime/data/raw_events_*.jsonl found"
  exit 2
fi
echo "[OK] latest=$LATEST"

echo
echo "=== [2] quick integrity checks ==="
LINES="$(wc -l < "$LATEST" | tr -d ' ')"
SIZE="$(stat -f '%z' "$LATEST" 2>/dev/null || echo 0)"
echo "[INFO] lines=$LINES size_bytes=$SIZE"
if [ "$LINES" -le 0 ] || [ "$SIZE" -le 0 ]; then
  echo "[FATAL] recorder file is empty; subscription worked but no events were written."
  exit 3
fi

echo
echo "=== [3] sample (first 2 / last 2) ==="
sed -n '1,2p' "$LATEST" || true
echo "----"
tail -n 2 "$LATEST" || true

echo
echo "=== [4] kind frequency (top 20) ==="
python3 - <<'PY'
import json, sys, collections, pathlib
p = pathlib.Path(sys.argv[1])
c = collections.Counter()
bad = 0
with p.open("r", encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        line=line.strip()
        if not line: 
            continue
        try:
            obj = json.loads(line)
            c[obj.get("kind","<none>")] += 1
        except Exception:
            bad += 1
print("[INFO] total_lines =", i)
print("[INFO] bad_json_lines =", bad)
for k,v in c.most_common(20):
    print(f"{k}\t{v}")
PY "$LATEST"

echo
echo "=== [5] update project board statuses (M0 broker connectivity DONE; next item DOING) ==="
python3 - <<'PY'
from pathlib import Path
p=Path("docs/board/PROJECT_BOARD.md")
t=p.read_text(encoding="utf-8")
t=t.replace("[~] Broker connectivity: Shioaji login + quote subscribe (TMF/TX/MTX + 2330/2317/2454) + raw event recorder",
            "[x] Broker connectivity: Shioaji login + quote subscribe (TMF/TX/MTX + 2330/2317/2454) + raw event recorder")
t=t.replace("[ ] Data store: schema v1 (events, bars, trades, orders, fills) + rotation",
            "[~] Data store: schema v1 (events, bars, trades, orders, fills) + rotation")
p.write_text(t,encoding="utf-8")
PY

echo
echo "=== [6] recompute progress header (Chinese) ==="
python3 - <<'PY'
import re, pathlib, datetime
board_path = pathlib.Path("docs/board/PROJECT_BOARD.md")
txt = board_path.read_text(encoding="utf-8")

def pct(done, total):
    return 0.0 if total == 0 else (done/total*100.0)

all_boxes = re.findall(r'^\s*-\s*\[( |x|~|!)\]\s+(.+)$', txt, flags=re.M)
total = len(all_boxes)
done = sum(1 for s,_ in all_boxes if s == 'x')

milestone = {}
blocks = re.split(r'(^###\s+.+$)', txt, flags=re.M)
for i in range(1, len(blocks), 2):
    h = blocks[i].strip()
    body = blocks[i+1]
    name = re.sub(r'^###\s+', '', h)
    boxes = re.findall(r'^\s*-\s*\[( |x|~|!)\]\s+(.+)$', body, flags=re.M)
    t = len(boxes)
    d = sum(1 for s,_ in boxes if s == 'x')
    milestone[name] = (d, t)

now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
lines = []
lines.append("# 專案進度總覽（自動計算）")
lines.append(f"- 更新時間：{now}")
lines.append(f"- 專案總完成度：{pct(done,total):.1f}% （已完成 {done} / {total} 項）")
lines.append("")
lines.append("## 里程碑完成度")
for k,(d,t) in milestone.items():
    lines.append(f"- {k}：{pct(d,t):.1f}% （已完成 {d} / {t}）")
lines.append("")
lines.append("## 說明（快速讀法）")
lines.append("- 看「專案總完成度」掌握全局；看「里程碑完成度」掌握目前在哪一段。")
lines.append("- [~] 進行中、[!] 阻塞、[x] 已完成。")
lines.append("")
progress_block = "\n".join(lines) + "\n"

marker_start = r'^#\s*專案進度總覽（自動計算）\s*$'
if re.search(marker_start, txt, flags=re.M):
    m = re.search(marker_start, txt, flags=re.M)
    start = m.start()
    anchors = []
    for pat in [r'\n##\s+Status Legend\b', r'\n#\s+TMF\b', r'\n#\s+TMF AutoTrader\b']:
        am = re.search(pat, txt)
        if am:
            anchors.append(am.start()+1)
    end = min(anchors) if anchors else len(txt)
    new_txt = txt[:start] + progress_block + "\n" + txt[end:]
else:
    new_txt = progress_block + "\n" + txt

board_path.write_text(new_txt, encoding="utf-8")
PY

if [ -x scripts/pm_tick.sh ]; then
  scripts/pm_tick.sh "M0: recorder verified (non-empty jsonl); broker connectivity marked DONE; data store set DOING"
fi

echo
echo "=== [OK] M0 recorder verification + board update done ==="
echo "=== [BOARD TOP 30] ==="
sed -n '1,30p' docs/board/PROJECT_BOARD.md
