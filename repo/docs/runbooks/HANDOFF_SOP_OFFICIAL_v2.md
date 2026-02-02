# HANDOFF_SOP_OFFICIAL_v2 (TMF AutoTrader / ULTRA / OFFICIAL-LOCKED)

## 0) 目標與定義

### 0.1 目標
在任何時刻（視窗容量上限、里程碑結束、例行換窗、緊急修復），都能做到：
- **100% 無縫接軌**：新視窗像同視窗續跑，不需要重新探索狀態、不需要猜測。
- **可驗收 / 可重建 / 可追溯**：交接包與環境以 HardGate 一鍵驗收，通過才進入開發。
- **One-Truth**：以最新 ULTRA WindowPack ZIP 為唯一事實來源（One-Doc / One-Truth）。

### 0.2 「100% 無縫接軌」的必要條件（必須同時成立）
1) **Pack HardGate PASS**：ZIP sha256 正確、解壓、`MANIFEST_SHA256_ALL_FILES.txt` 全檔 sha256 全 PASS  
2) **Env Rebuild HardGate PASS**：python/venv/pip-freeze 指紋、關鍵檔案 sha256、LaunchAgents existence 等基線 PASS  
3) **Opening Prompt Seal PASS**：ZIP 內含  
   - `repo/runtime/handoff/state/NEW_WINDOW_OPENING_PROMPT_ULTRA_ZH.md`  
   - `repo/runtime/handoff/state/NEW_WINDOW_OPENING_PROMPT_ULTRA_ZH.md.sha256.txt`  
   - `repo/docs/handoff/NEW_WINDOW_OPENING_PROMPT_FINAL.md` 且 header 必為：  
     `# NEW WINDOW OPENING PROMPT (FINAL, AUTO-UPDATED)`

只要以上任一項不成立，視為「未達到無縫接軌」。

---

## 1) 永久規則（OFFICIAL-LOCKED / v18 One-Truth）

1) `docs/bibles/TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18.md` 為唯一規範（One-Truth）。任何衝突以 v18 為準。
2) **不可暗改 / 靜默改寫**：所有狀態記錄要 append-only（例：handoff log、audit report）。允許覆寫的檔案必須明確標註（例如 DRAFT 類型）。
3) **一鍵 HardGate 是進入開發的門檻**：新視窗第一件事永遠是 HardGate（pack + env）。
4) **One command per turn**：在 ChatGPT 協作流程中，執行 Terminal 時遵守「每回合只跑一個指令」協定（由助理給一個指令→使用者貼回輸出→下一步）。
5) 新增功能/排程如需動到 ops 或 LaunchAgents，一律採「新增獨立項」方式，不得破壞既有主線（避免影響可重現性）。

---

## 2) 必備交接物（你永遠只需要準備這些）

### 2.1 最小必備（Minimal Required）
- `runtime/handoff/latest/TMF_AutoTrader_WindowPack_ULTRA_*.zip`
- 同名 `.zip.sha256.txt`

> **規則：只看 `runtime/handoff/latest/` 最新一份**（以檔案時間最新為準）。

### 2.2 ULTRA ZIP 內必須包含（Hard Requirements）
- `MANIFEST_SHA256_ALL_FILES.txt`
- `HANDOFF_ULTRA.md`
- `repo/docs/bibles/TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18.md` + `.sha256.txt`
- `repo/runtime/handoff/state/NEW_WINDOW_OPENING_PROMPT_ULTRA_ZH.md` + `.sha256.txt`
- `repo/docs/handoff/NEW_WINDOW_OPENING_PROMPT_FINAL.md`（FINAL header）
- `state/audit_report_latest.md`
- `state/env_rebuild_report_latest.md`（若已導入 env hardgate）

---

## 3) 新視窗「你要貼什麼」：兩種模式（推薦用 B）

### 3.1 SOP-A（最省事 / 最短）
> 適合：容量爆了、只想快速切窗  
新視窗第一則訊息只貼這一句（並附上 latest ZIP + sha）：

- 「請以附檔 latest ULTRA WindowPack ZIP 為 One-Truth；第一步先跑 HardGate（Pack HardGate + Env Rebuild HardGate），兩者 PASS 後再依 `state/next_step.txt` 繼續。」

### 3.2 SOP-B（最穩健 / 推薦）
> 適合：幾乎所有情境（避免平台附件讀取順序造成阻力）  
新視窗第一則訊息貼以下「四行摘要」（並附上 latest ZIP + sha）：

1) 「One-Truth：以附檔 latest ULTRA ZIP 為唯一事實來源。」  
2) 「第一步：執行 Pack HardGate；必須 PASS。」  
3) 「第二步：執行 Env Rebuild HardGate；必須 PASS。」  
4) 「PASS 後：照 `state/next_step.txt` 做下一步；全程 One command per turn。」

---

## 4) 各情境 SOP（照做即可，不用思考）

> NOTE：以下流程描述會提到“執行某個腳本”。在 ChatGPT 協作時，請仍遵守 one-command-per-turn（一次只貼/跑一個 terminal command）。

---

### 情境 1：視窗容量突然達上限（緊急交接 / Emergency Cutover）

#### 你要附什麼？
- 必附：latest ULTRA ZIP + `.sha256.txt`

#### 新視窗要做什麼（必做）
1) **Pack HardGate（必須 PASS）**
   - PASS 標準：
     - zip sha256 檢查 OK
     - unzip OK
     - `MANIFEST_SHA256_ALL_FILES.txt` 全 PASS
2) **Env Rebuild HardGate（必須 PASS）**
   - PASS 標準：
     - python3 = 3.9.x（基線 3.9.6）
     - `.venv` OK 且 venv python = 3.9.x
     - pip-freeze sha256 指紋存在（不要求值固定，但要求可生成且可追蹤）
     - 關鍵檔案存在且 sha256 可計算（至少 v18、configs、mk_windowpack、audit hardgate 等）
3) **讀 `state/next_step.txt`** 作為下一步唯一來源（除非你在新視窗明確指定覆寫）

#### FAIL 分支（任一 HardGate FAIL）
- 一律停止開發（不進入任何 code 修改）
- 先修 HardGate：修腳本/修環境/重打包
- 修好後重新跑 HardGate，PASS 才繼續

---

### 情境 2：重大里程碑完成，想正式封存交接（Milestone Close）

#### 你在舊視窗/本機要做什麼
1) 先觸發一次 **ULTRA 打包**（確保 opening prompt / audit / env 報告都最新）
2) 確認 `runtime/handoff/latest/` 出現最新 ZIP + sha256 sidecar
3) 確認 ZIP 內的 opening prompt header 為 FINAL（不是 DRAFT）

#### 新視窗要做什麼
- 一律用 SOP-B 開場（四行摘要）
- 一律先 HardGate（pack + env）
- PASS 後依 `next_step.txt` 或由你明確指定「新階段第一個任務」

---

### 情境 3：只是想換視窗繼續開發（Routine Switch）

#### 你要附什麼
- latest ULTRA ZIP + sha256 sidecar

#### 新視窗要做什麼
1) Pack HardGate PASS
2) Env Rebuild HardGate PASS
3) next_step.txt 繼續

> 你可以不貼整篇開場白；但仍建議貼 SOP-B 四行摘要，避免任何附件讀取順序問題。

---

### 情境 4：你要新視窗一開場就跑「指定任務」（Task-First Cutover）
例如：你希望新視窗第一步就跑 sweep、refactor、canary、paper-live glue 等。

#### 你要附什麼
- latest ULTRA ZIP + sha256 sidecar

#### 新視窗要貼什麼
- SOP-B 四行摘要 + 第五行「指定任務」
- 第五行格式（固定模板）：
  - 「HardGate PASS 後，立刻執行：<任務名/腳本>，成功標準：<一句話驗收標準>。」

#### 新視窗要做什麼
1) HardGate（pack + env）都 PASS
2) 立刻執行指定任務
3) 任務完成後更新 next_step 或 board/changelog（依 v18 規範）

---

### 情境 5：你懷疑環境被污染、想先驗收再做任何事（Environment Suspicion / Quarantine Mode）

#### 新視窗流程（強制）
1) Env Rebuild HardGate PASS（先做）
2) Pack HardGate PASS（再做）
3) PASS 後才進入開發

#### FAIL 分支
- Env FAIL：優先修環境（python/venv/pip/paths），修好再驗
- Pack FAIL：優先重打包或修打包腳本，再驗

---

## 5) HardGate 一鍵驗收（操作標準）

### 5.1 Pack HardGate（目的）
確認交接包本身完整性：sha256、解壓、manifest 全檔一致。

#### PASS 標準（缺一不可）
- ZIP sha256 `OK`
- unzip 成功
- `MANIFEST_SHA256_ALL_FILES.txt` 逐檔 `OK`
- opening prompt seal 檢查 `OK`
- v18 sha256 vs sidecar `OK`

### 5.2 Env Rebuild HardGate（目的）
確認環境可重建性：python 3.9、venv、依賴指紋、關鍵檔案存在與可哈希。

#### PASS 標準（缺一不可）
- python3 = 3.9.x（基線 3.9.6）
- `.venv` 存在且 venv python = 3.9.x
- `pip freeze` 可產生且 sha256 可計算（形成 fingerprint）
- 關鍵檔案 existence + sha256 可計算（至少列在 env report 中的那批）
- LaunchAgents 目錄存在且 tmf_autotrader plists existence OK

---

## 6) 「只附 ZIP，不貼開場白」是否允許？

允許，但有條件：
- 你必須在新視窗至少貼 SOP-A 那一句（One-Truth + 先 HardGate + next_step）
- 且 ZIP 內必須包含：
  - `NEW_WINDOW_OPENING_PROMPT_ULTRA_ZH.md(+sha)`
  - `NEW_WINDOW_OPENING_PROMPT_FINAL.md`（FINAL header）
  - `HANDOFF_ULTRA.md`
  - `MANIFEST_SHA256_ALL_FILES.txt`

> 最穩健做法仍是 SOP-B 四行摘要。這不是為了「資訊更多」，而是把平台/UI的不可控風險壓到接近 0。

---

## 7) 常見故障與排除（照表處理）

### 7.1 sha256 檢查報「No such file or directory」
**原因**：在錯的工作目錄執行 `shasum -c`，sidecar 內寫的是相對路徑或不同 basename。  
**處理**：
- 一律改成「用 zip 的完整路徑去驗」，或在 sidecar 同一目錄執行。
- 修 HardGate 腳本：確保 `shasum -a 256 -c` 在正確 cwd。

### 7.2 ZIP 內 header 顯示 DRAFT 而非 FINAL
**原因**：生成 DRAFT 的地方覆蓋 FINAL 或 pack 未更新。  
**處理**：
- 修生成器/腳本，確保 pack 時寫入 FINAL header
- 重新 mk_windowpack_ultra 打包，直到 ZIP 內 FINAL header 正確

### 7.3 Opening prompt 沒被 seal 進 zip
**原因**：seal 條件未觸發或 zip 不是最新。  
**處理**：
- 先生成 `runtime/handoff/state/NEW_WINDOW_OPENING_PROMPT_ULTRA_ZH.md(+sha)`
- 再重新打包 ULTRA
- 用 `unzip -l` 確認兩檔都在

### 7.4 Env HardGate PASS 但 venv python 不是 3.9.x
**處理**：
- 視為 FAIL（不得進入開發）
- 重建 venv 使用 python3.9 基線後再驗

---

## 8) 交接成功的最終判定（你不用想，照這個看）

當你在新視窗看到：
- Pack HardGate：`[PASS]`  
- Env Rebuild HardGate：`[PASS]`  
- 且 `state/next_step.txt` 可直接指引下一步

=> 判定：**100% 無縫接軌達成，可像同視窗續跑。**

(End)
