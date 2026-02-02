#!/usr/bin/env bash
set -euo pipefail
PROJ="$HOME/tmf_autotrader"
cd "$PROJ"

python3 - <<'PY'
import re, pathlib, datetime
p = pathlib.Path("docs/board/PROJECT_BOARD.md")
txt = p.read_text(encoding="utf-8")

boxes = re.findall(r'^\s*-\s*\[( |x|~|!)\]\s+(.+)$', txt, flags=re.M)
total = len(boxes)
done = sum(1 for s,_ in boxes if s == 'x')

def pct(d,t): return 0.0 if t==0 else (d/t*100.0)

milestone = {}
parts = re.split(r'(^###\s+.+$)', txt, flags=re.M)
for i in range(1, len(parts), 2):
    name = re.sub(r'^###\s+', '', parts[i].strip())
    body = parts[i+1]
    b = re.findall(r'^\s*-\s*\[( |x|~|!)\]\s+(.+)$', body, flags=re.M)
    t = len(b); d = sum(1 for s,_ in b if s == 'x')
    milestone[name]=(d,t)

now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
hdr = []
hdr.append("# 專案進度總覽（自動計算）")
hdr.append(f"- 更新時間：{now}")
hdr.append(f"- 專案總完成度：{pct(done,total):.1f}% （已完成 {done} / {total} 項）")
hdr.append("")
hdr.append("## 里程碑完成度")
for k,(d,t) in milestone.items():
    hdr.append(f"- {k}：{pct(d,t):.1f}% （已完成 {d} / {t}）")
hdr.append("")
hdr.append("## 說明（快速讀法）")
hdr.append("- 看「專案總完成度」掌握全局；看「里程碑完成度」掌握目前在哪一段。")
hdr.append("- [~] 進行中、[!] 阻塞、[x] 已完成。")
hdr = "\n".join(hdr) + "\n\n"

marker = r'^#\s*專案進度總覽（自動計算）\s*$'
if re.search(marker, txt, flags=re.M):
    m = re.search(marker, txt, flags=re.M)
    start = m.start()
    anchors=[]
    for pat in [r'\n##\s+Status Legend\b', r'\n#\s+TMF\b', r'\n#\s+TMF AutoTrader\b']:
        am=re.search(pat, txt)
        if am: anchors.append(am.start()+1)
    end=min(anchors) if anchors else len(txt)
    txt = txt[:start] + hdr + txt[end:]
else:
    txt = hdr + txt

p.write_text(txt, encoding="utf-8")
PY

MSG="${1:-pm_refresh_board}"
"$PROJ/scripts/pm_tick.sh" "$MSG"
