# PROJECT_BOARD AutoSync 憲法級原則（Constitution Bible）v1

> 本文件為 TMF AutoTrader 專案「憲法級」最高指導原則（最高優先序）。
> 目的：確保 `docs/board/PROJECT_BOARD.md` 的進度/狀態可 100% 穩定自動更新，並且永遠不再為了 board 問題脫離主線除錯。

---

## 0. 定義與範圍

- **Canonical Entrypoint（唯一入口）**：`scripts/pm_refresh_board_canonical.sh`
- **Board**：`docs/board/PROJECT_BOARD.md`
- **Changelog**：`docs/board/CHANGELOG.md`
- **驗證腳本**：`scripts/verify_pm_refresh_board_v1.sh`
- **legacy 工具**：任何舊入口/舊文檔/舊字串（包含 literal `pm_refresh_board.sh`）皆視為禁止依賴物

---

## 1. 憲法級不可變原則（Hard Invariants）

1) **唯一入口原則（One-Entrypoint Rule）**
   - 任何自動化（launchd / pm_tick / pre-commit / runner / daily pack）只能呼叫：
     - `scripts/pm_refresh_board_canonical.sh <tag>`
   - 不得直接呼叫舊版 entrypoint 或以任何方式繞過 canonical。

2) **Board-only 變更原則（Allowlist Rule）**
   - Board refresh 的允許變更檔案只限：
     - `docs/board/PROJECT_BOARD.md`
     - `docs/board/CHANGELOG.md`
   - 若 refresh 導致其他檔案產生 working-tree diff，必須視為 **BLOCK（禁止提交、禁止繼續主線）**，先修復 refresh 行為。

3) **Idempotent 原則（可重複執行必須結果一致）**
   - 連續執行 canonical refresh 兩次以上，除了合理的「時間戳/Changelog append」外，不得產生不可解釋漂移。
   - Header 的統計數字必須可由內容可推導（done/doing/blocked/todo/pct），不可手改。

4) **Legacy Literal 零殘留原則（Zero Legacy Literal）**
   - repo 主線（排除 `runtime/handoff` 與 `*.bak*`）不得殘留 legacy literal：
     - `pm_refresh_board.sh`
   - 任何需要提及 legacy 的情境，必須以「token-split」或等效方式避免 literal 回歸，並在驗證中確保 grep 為 0 hit。

5) **提交前強制門禁（Pre-commit Gate）**
   - `.githooks/pre-commit` 必須：
     - 僅優先呼叫 canonical
     - 只 add allowlist
     - 若 allowlist 以外變更 -> BLOCK exit non-zero
   - 任何人/任何視窗不得關閉此門禁。

---

## 2. 必跑驗證（HardGate Checklist）

在以下任一情境發生時，必須跑完整 HardGate：
- 新視窗接手後第一次開發前
- 修改任何 scripts/board / docs/board / pm_tick / runner / pre-commit 相關檔案後
- 打包 WindowPack / FullPack 前

HardGate 必須同時滿足：

A. Refresh + Verify
- `bash scripts/pm_refresh_board_canonical.sh <tag>`
- `bash scripts/verify_pm_refresh_board_v1.sh` 必須 PASS（m6/m8/progress/header 全 OK）

B. Zero Legacy Literal
- 全 repo（排除 `runtime/handoff` + `*.bak*`）grep `pm_refresh_board.sh` 結果必須為 **0 hit**

---

## 3. 變更控制（Change Control / Patch Discipline）

- 本憲法級系統**不得任意更改**。任何修改必須走「受控變更」流程：
  1) 先提出變更原因（必須是穩定性/可驗證性提升，且不得破壞主線）
  2) 同步更新本 Bible（版本 +1：v1 -> v2…）
  3) 重新產生 sha256 sidecar
  4) 跑完 HardGate Checklist（必須 PASS）
  5) 變更需可被新視窗 0-gap 接手，不得要求新視窗重新理解/重新除錯

---

## 4. 故障處置（絕不拖主線）

若未來出現任何 board refresh 問題：
- **立即停止新增功能開發（Freeze mainline）**
- 先恢復到「最後一次 HardGate PASS」的狀態（以 commit/patch 為準）
- 只有當 HardGate 再次 PASS，才能回到主線任務

---

## 5. 本憲法文件的地位（最高優先序）

- 本文件為 TMF AutoTrader 專案最高指導原則。
- 若任何文件/腳本與本文件衝突，以本文件為準；需修正衝突來源，並跑 HardGate 回歸驗證。
