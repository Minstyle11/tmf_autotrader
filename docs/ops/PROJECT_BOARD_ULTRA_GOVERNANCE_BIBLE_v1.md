# PROJECT_BOARD ULTRA 治理聖經（憲法級）v1

> 憲法級規範（本專案全視窗 100% 強制遵守、不可逾越、不可擅自變更）  
> 目的：永遠杜絕 PROJECT_BOARD 壞掉/爆量/分母被污染，未來任何新視窗 **0 回合** 除錯/修復 board。

---

## 1) 唯一真相與範圍

### 1.1 唯一真相（One-Truth）
- **主線進度（CANON）唯一真相：** `docs/board/PROJECT_BOARD.md` 內的 `<!-- AUTO:PROGRESS_BEGIN --> ... <!-- AUTO:PROGRESS_END -->`
  - 任何統計/顯示/報表不得用「掃整份 Markdown 的 TASK 行」取代此區塊。
- **Patch 任務（PATCH）唯一真相：** `<!-- AUTO_PATCH_TASKS_START --> ... <!-- AUTO_PATCH_TASKS_END -->`
  - PATCH 必須獨立統計，**不得污染 CANON 分母**（避免再發生 576 爆量/完成度歸零）。

### 1.2 檔案與腳本（憲法級）
- Board：`docs/board/PROJECT_BOARD.md`
- HardGate（Fail-Fast）：`scripts/board_ultra_hardgate_v1.py`
- 一鍵修復器（Idempotent Repair）：`scripts/ops_board_ultra_repair_v1.py`
- Refresh+Verify（已掛 HardGate）：`scripts/pm_refresh_board_and_verify.sh`
- 統計顯示（以 AUTO:PROGRESS 為準）：`scripts/board_canonical_counts_v1.py`（可維持 uchg 鎖檔）

---

## 2) 不可逾越的硬規則（Fail-Fast Invariants）

以下任一條違反，視為「BOARD 失效」，**不得繼續任何開發/打包/交接**，必須先修復：

### 2.1 Legacy wrapper 必須唯一且順序正確
- `<!-- AUTO:PATCH_TASKS_BEGIN -->`、`<!-- AUTO:PATCH_TASKS_END -->` 各只能出現一次
- 且必須滿足：  
  `LEG_BEGIN < AUTO_PATCH_TASKS_START < AUTO_PATCH_TASKS_END < LEG_END`
- 任何 legacy marker 出現在 wrapper 之外 → 立即 FAIL

### 2.2 禁止 patch 任務漂流到 patch block 之外（根因封殺）
- 在 `AUTO_PATCH_TASKS_START/END` 區塊之外，**嚴禁**出現字串：`[TASK:M8-`
- 這是造成「TASK_total 爆量（例如 576）」的唯一最大根因，屬於憲法級禁止事項。

### 2.3 refresh 必須 fail-fast
- `scripts/pm_refresh_board_and_verify.sh` **必須**先跑 `scripts/board_ultra_hardgate_v1.py`
- HardGate FAIL → refresh 直接退出（不可繼續寫 board）

---

## 3) 標準作業流程（唯一允許的操作路徑）

### 3.1 平時刷新（唯一允許）
- 一律使用：
  - `bash scripts/pm_refresh_board_and_verify.sh`
- 禁止手動「大量貼 code 到 zsh 命令列」修改 board（會引發 quote>/dquote>/command too long 等災難）。

### 3.2 出現 FAIL 時（唯一允許的修復）
- 只允許跑「一鍵修復器」：
  - `python3 scripts/ops_board_ultra_repair_v1.py`
- 修復器必須具備：
  - 先備份 `.bak_ULTRA_*`
  - idempotent（重複跑不會越修越壞）
  - 修復後自動跑：HardGate → pm_refresh_board_and_verify → PASS 才算完成

---

## 4) 鎖檔策略（避免被回寫）

### 4.1 可鎖檔（建議鎖）
- `scripts/board_canonical_counts_v1.py`（已被驗證會被回寫成壞版本時）
- Bible 文件本身（本檔）

### 4.2 解鎖/改版規範（唯一允許）
- 若要更新憲法級規範：
  1) `chflags nouchg <file>`
  2) 僅允許「版本號升級」方式更新（v1 → v2…），不得直接覆蓋舊版  
  3) 產生 `.sha256.txt` sidecar  
  4) `chflags uchg <file>`

---

## 5) 驗收步驟（逐步）/ Acceptance Steps

### A. HardGate 驗收
1) 執行：
   - `python3 scripts/board_ultra_hardgate_v1.py`
2) 預期輸出：
   - `[PASS][BOARD_HARDGATE] OK`

### B. Refresh+Verify 驗收
1) 執行：
   - `bash scripts/pm_refresh_board_and_verify.sh`
2) 預期輸出包含：
   - `[PASS][BOARD_HARDGATE] OK`
   - `[PASS] verify_pm_refresh_board_v1: ... all OK`

### C. Repair 驗收（只在 FAIL 時使用）
1) 執行：
   - `python3 scripts/ops_board_ultra_repair_v1.py`
2) 預期輸出包含：
   - `[PASS] repair -> hardgate -> pm_refresh all OK`

### D. 計數一致性驗收（主線分母不得被 PATCH 污染）
1) 執行：
   - `python3 scripts/board_canonical_counts_v1.py`
2) 預期：
   - `[CANON] total=... done=... pct=...` 與 board header 的 AUTO:PROGRESS 一致
   - `[PATCH] total=...` 為 patch block 的獨立統計

---

## 6) 憲法級承諾（對未來所有新視窗）

- 未來任何新視窗：  
  **不得花任何回合修 PROJECT_BOARD。**  
  若 HardGate FAIL：只允許跑 Repair；修完必 PASS 才能繼續。
- 任何人（包含助理）不得擅自改變本規範與腳本的核心不變量；若要更動，只能走「版本升級 + sha256」流程。
