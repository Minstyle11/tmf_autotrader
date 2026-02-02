#!/usr/bin/env bash
set -euo pipefail

PROJ="$HOME/tmf_autotrader"
cd "$PROJ"

git config --global init.defaultBranch main >/dev/null 2>&1 || true
if [ "$(git branch --show-current 2>/dev/null || true)" = "master" ]; then
  git branch -m main || true
fi

mkdir -p scripts runtime/logs docs/board configs/secrets "$HOME/Library/LaunchAgents"

# --- Changelog (append-only) ---
if [ ! -f docs/board/CHANGELOG.md ]; then
  cat > docs/board/CHANGELOG.md <<'EOF'
# 變更紀錄 Changelog（只追加、不回寫）
- 此檔案由腳本自動更新，用於跨視窗、跨日期追溯每次重大變更。
EOF
fi

cat > scripts/pm_tick.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
PROJ="$HOME/tmf_autotrader"
TS="$(date '+%F %T')"
MSG="${1:-auto}"
echo "- [$TS] $MSG" >> "$PROJ/docs/board/CHANGELOG.md"
EOF
chmod +x scripts/pm_tick.sh

# --- Backup script ---
cat > scripts/backup_to_external.sh <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

PROJ="$HOME/tmf_autotrader"
STAMP="$(date +%F_%H%M%S)"
LOG_DIR="$PROJ/runtime/logs"
mkdir -p "$LOG_DIR"

TARGET_VOL=""

for v in /Volumes/*; do
  [ -d "$v" ] || continue
  if [ -f "$v/.tmf_autotrader_backup_target" ] && [ -w "$v" ]; then
    TARGET_VOL="$v"; break
  fi
done

if [ -z "$TARGET_VOL" ]; then
  for v in /Volumes/*; do
    [ -d "$v" ] || continue
    base="$(basename "$v")"
    case "$base" in
      "Macintosh HD"|"Macintosh HD - Data"|"Preboot"|"Recovery"|"Update"|"VM") continue;;
    esac
    if [ -w "$v" ]; then TARGET_VOL="$v"; break; fi
  done
fi

if [ -z "$TARGET_VOL" ]; then
  echo "[BACKUP][FAIL] No writable external volume found under /Volumes." | tee -a "$LOG_DIR/backup.err.log"
  echo "請插入外接硬碟；建議鎖定目標：touch /Volumes/<DRIVE>/.tmf_autotrader_backup_target" | tee -a "$LOG_DIR/backup.err.log"
  exit 2
fi

DEST_ROOT="$TARGET_VOL/tmf_autotrader_backups"
DEST="$DEST_ROOT/$STAMP"
mkdir -p "$DEST_ROOT"

rsync -a --delete \
  --exclude ".git/" \
  --exclude ".venv/" --exclude ".venv-*/" \
  --exclude "__pycache__/" --exclude "*.pyc" \
  --exclude ".DS_Store" \
  "$PROJ/" "$DEST/"

ln -sfn "$DEST" "$DEST_ROOT/latest"
echo "[BACKUP][OK] target=$TARGET_VOL dest=$DEST" | tee -a "$LOG_DIR/backup.out.log"
EOF
chmod +x scripts/backup_to_external.sh

# --- LaunchAgent ---
PLIST="$HOME/Library/LaunchAgents/com.tmf_autotrader.backup.plist"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key><string>com.tmf_autotrader.backup</string>
    <key>ProgramArguments</key>
    <array>
      <string>$PROJ/scripts/backup_to_external.sh</string>
    </array>
    <key>RunAtLoad</key><true/>
    <key>StartInterval</key><integer>1800</integer>
    <key>StandardOutPath</key><string>$PROJ/runtime/logs/launchagent_backup.out.log</string>
    <key>StandardErrorPath</key><string>$PROJ/runtime/logs/launchagent_backup.err.log</string>
  </dict>
</plist>
EOF

USER_UID="$(id -u)"
launchctl bootout "gui/$USER_UID/com.tmf_autotrader.backup" 2>/dev/null || true
launchctl bootstrap "gui/$USER_UID" "$PLIST"
launchctl enable "gui/$USER_UID/com.tmf_autotrader.backup"
launchctl kickstart -k "gui/$USER_UID/com.tmf_autotrader.backup" || true

# --- PM board progress % (Chinese header) ---
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

"$PROJ/scripts/pm_tick.sh" "Fixed UID readonly bug; installed backup LaunchAgent; PM board % updated"

echo "=== [OK] setup complete ==="
echo "PLIST=$PLIST"
launchctl list | grep -F "com.tmf_autotrader.backup" || true
tail -n 20 "$PROJ/runtime/logs/backup.out.log" 2>/dev/null || true
tail -n 20 "$PROJ/runtime/logs/backup.err.log" 2>/dev/null || true
sed -n '1,30p' "$PROJ/docs/board/PROJECT_BOARD.md" || true
