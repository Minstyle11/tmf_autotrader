#!/usr/bin/env bash
set -euo pipefail

PROJ="$HOME/tmf_autotrader"
cd "$PROJ"

P="$(cat runtime/handoff/state/latest_ultra_zip_path.txt 2>/dev/null || true)"
if [ -z "${P:-}" ]; then
  P="$(ls -1t runtime/handoff/latest/TMF_AutoTrader_WindowPack_ULTRA_*.zip 2>/dev/null | head -n 1 || true)"
fi
if [ -z "${P:-}" ] || [ ! -f "$P" ]; then
  echo "[FATAL] cannot locate latest ULTRA zip. got: '${P:-}'" >&2
  exit 2
fi

SHA_SIDE="${P}.sha256.txt"
if [ ! -f "$SHA_SIDE" ]; then
  echo "[FATAL] missing zip sha256 sidecar: $SHA_SIDE" >&2
  exit 3
fi

OUT="runtime/handoff/state/NEW_WINDOW_CLIPBOARD_ULTRA_ZH.txt"
cat > "$OUT" <<EOF
【新視窗交接（ULTRA / OFFICIAL-LOCKED / 100%無縫）】

我已附上最新交接包（只認這個為 One-Truth）：
- $P
- $SHA_SIDE

請依照 repo/docs/bibles/HANDOFF_SOP_OFFICIAL_BIBLE_v1.md 執行：
1) Pack HardGate（zip sha256 -> unzip -> MANIFEST_SHA256_ALL_FILES 全檔PASS）
2) Env Rebuild HardGate（env_rebuild_report_latest.md 對齊）
3) 讀取 repo/docs/handoff/NEW_WINDOW_OPENING_PROMPT_FINAL.md 的 Next step
4) 之後嚴格「每回合只給我一個 Terminal 指令」繼續主線開發。
EOF

shasum -a 256 "$OUT" > "${OUT}.sha256.txt"

echo "[OK] wrote: $OUT"
echo "[OK] wrote: ${OUT}.sha256.txt"
