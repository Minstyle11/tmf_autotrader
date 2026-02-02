# HANDOFF SOP (OFFICIAL) v1 — 100% 無縫接軌（TMF AutoTrader）

狀態：OFFICIAL-LOCKED（除非以「明確版本 bump + CHANGELOG 記錄 + Bible/Runbook 更新」方式發布，否則不得改寫規則。）

---

## 0. 目的與不變條款（不可違抗）
### 0.1 目標
- **任何時候開新視窗都 100% 無縫接軌**：新視窗不需要重新回憶/重查/重建上下文，直接接手主線開發。

### 0.2 不變條款
- **Append-only**：`docs/handoff/HANDOFF_LOG.md` 永不允許在打包或任何流程中被 truncate/覆寫（只能追加）。
- **next_step 為單一真相來源**：下一步唯一終端指令必須寫入 `runtime/handoff/state/next_step.txt`。
- **一鍵 ZIP 只在容量風險或明確切窗時執行**：平時只做持續記錄，不做頻繁打包。
- **一回合一指令**：所有跨視窗接手後的互動仍遵守一回合只執行一個 Terminal 指令。

---

## 1. 系統構成（你現在的自動化鏈路）
### 1.1 持續自動記錄（LaunchAgent）
`com.tmf_autotrader.handoff_tick` 每 300 秒執行一次：
1) `scripts/handoff_state_snapshot_v1.sh` → 更新 `runtime/handoff/state/latest_state.json`
2) `scripts/handoff_tick.sh` → append-only 更新 `docs/handoff/HANDOFF_LOG.md`，並重建 `docs/handoff/NEW_WINDOW_OPENING_PROMPT_DRAFT.md`

### 1.2 人工指定「下一步」的唯一出口
- `runtime/handoff/state/next_step.txt`
- 原則：內容必須 **可直接 copy/paste 執行**；若含 heredoc，delimiter 必須完整閉合。

### 1.3 一鍵打包（僅在必要時）
- 腳本：`scripts/mk_windowpack_ultra.sh`
- 產物：`runtime/handoff/latest/TMF_AutoTrader_WindowPack_ULTRA_*.zip` + `.sha256.txt`
- ZIP 內必含：`MANIFEST_SHA256_ALL_FILES.txt`（pack root 全檔案 sha256）

---

## 2. 舊視窗尾端 SOP（平時如何維持永不斷鏈）
> 平時「不打包」，只做「寫 next_step + 記錄一次 tick」。

### 2.1 每完成一個小步驟（或要切主題）必做：更新 next_step
- 將「下一步唯一 Terminal 指令」寫入：
  - `~/tmf_autotrader/runtime/handoff/state/next_step.txt`
- 要求：
  - 可直接執行（copy/paste）
  - heredoc/子腳本需完整閉合（避免 delimiter 截斷）
  - 避免在外層 heredoc 內容中出現會撞到 delimiter 的單獨一行 token

### 2.2 更新 next_step 後必做：記錄一次 handoff_tick
- 執行：`./scripts/handoff_tick.sh "set_next_step_<reason>_<timestamp>"`
- 目的：把「board/changelog/git/next_step」鎖進 append-only chain（HANDOFF_LOG）。

### 2.3 異常診斷（不急著打包）
若懷疑鏈路異常，先看：
- `runtime/logs/launchagent_handoff_tick.err.log`
- `docs/handoff/HANDOFF_LOG.md` 最末段是否有更新時間
只要 handoff_tick 仍在持續寫、latest_state.json 仍更新，即視為鏈路 OK。

---

## 3. 何時必須打包（ULTRA）
符合任一條就打包：
1) 準備開新視窗（切窗）
2) 助理判斷目前視窗進入容量風險
3) 要做高風險操作前先做保險快照（大改風控/重構/資料格式變更）

---

## 4. 舊視窗打包 SOP（ULTRA）
### 4.1 執行
- `./scripts/mk_windowpack_ultra.sh`

### 4.2 最低驗收（必做）
1) ZIP sidecar：
- `shasum -c runtime/handoff/latest/TMF_AutoTrader_WindowPack_ULTRA_*.zip.sha256.txt` → 必須 OK
2) 解壓後 pack root 必含：
- `MANIFEST_SHA256_ALL_FILES.txt`
3) manifest verify：
- 依 manifest 對 pack root 全檔案逐一 sha256 驗證 → 必須全 PASS

---

## 5. 新視窗開場 SOP（100% 無縫接手）
### 5.1 上傳
上傳「最新一包」：
- `TMF_AutoTrader_WindowPack_ULTRA_*.zip`
- `TMF_AutoTrader_WindowPack_ULTRA_*.zip.sha256.txt`

### 5.2 新視窗第 1 步：驗 ZIP sha256
- `shasum -c *.zip.sha256.txt` → 必須 OK，否則停止

### 5.3 新視窗第 2 步：解壓 + 驗 manifest
- 解壓得到 `tmf_autotrader_windowpack_ultra_YYYYMMDD_HHMMSS/`
- 驗 `MANIFEST_SHA256_ALL_FILES.txt` 全檔案 sha256 必須 PASS

### 5.4 新視窗第 3 步：讀 prompt + 讀 next_step
- 讀 `NEW_WINDOW_OPENING_PROMPT_FINAL.md`（當下狀態）
- 讀 `state/next_step.txt`（下一步唯一終端指令）

### 5.5 新視窗第 4 步：直接執行 next_step
- 只執行 next_step（一回合一指令）
- 貼回輸出給助理 → 進入下一步迭代

---

## 6. 永久避坑規則（shell/heredoc）
- 一律優先用：`cat <<'BASH' | bash` 讓 bash 接管（避免 zsh 差異）
- 避免 nested heredoc delimiter 相撞（外層/內層 token 要不同，且內容不要出現同名單獨一行）
- next_step 內容務必閉合 `PY/BASH/EOF` 等 delimiter
