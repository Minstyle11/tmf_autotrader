# PROJECT_BOARD Auto Progress Bible v1 (OFFICIAL-LOCKED)

## 0. 目的
確保 docs/board/PROJECT_BOARD.md 的「專案總完成度」永遠由同一套 Canonical 規則全自動、可重現、100% 正確地更新；直到 TMF AutoTrader 專案結案前不得偏離。

## 1. 唯一權威規則（One-Truth）
1) PROJECT_BOARD 的進度統計唯一權威區塊：
- <!-- AUTO_PROGRESS_START --> 到 <!-- AUTO_PROGRESS_END -->

2) 進度統計唯一權威計算器：
- scripts/update_project_board_progress_v2.py（canonical / no-regex 解析器）

3) 自動刷新唯一入口（排程/人工都必須走這個）：
- scripts/pm_refresh_board_canonical.sh

4) LaunchAgent 唯一允許的呼叫：
- com.tmf_autotrader.pm_tick.plist 只能呼叫 pm_refresh_board_canonical.sh（不得再呼叫舊版 pm_refresh_board (legacy)）

## 2. Canonical Task 定義（必須完全一致）
一行必須同時滿足才算「任務」：
- 去除前置空白後，第一個字元是 - 或 * 或 +
- 前 0~4 個字元內出現 [ 與 ]，且中間是 checkbox 狀態
- ] 之後必須有 title（非空）
- checkbox 狀態：
  - [x] / [X] => done
  - [~]       => doing
  - [!]       => blocked
  - [ ]       => todo
- 必須忽略：
  - fenced code block（``` 之間）
  - AUTO_PROGRESS 區塊本身（避免自我計算）
  - 其他任何舊進度區塊（見 §3 清理）

## 3. 舊進度殘留的「強制清理」政策（必做）
每次 canonical 更新時，必須清掉下列任何殘留，避免出現多份進度口徑：
- <!-- AUTO:PROGRESS_BEGIN --> ... <!-- AUTO:PROGRESS_END -->
- 任何包含「專案總完成度」且不是位於 AUTO_PROGRESS_START/END 之間的行
- 其他歷史進度標記（若未來發現新殘留，需以 v1.x patch 方式加入清理規則）

## 4. 產出與稽核（Evidence）
每次更新必須寫出 audit：
- runtime/handoff/state/PROJECT_BOARD_CANONICAL_TASK_AUDIT_YYYYMMDD_HHMMSS.md
內容至少包含：total/done/doing/blocked/todo/invalid_like，並列出 invalid_like 原始行。

## 5. 驗收步驟（逐步）
1) 手動跑一次 canonical 更新：
   - python3 scripts/update_project_board_progress_v2.py
2) 開啟 docs/board/PROJECT_BOARD.md 檢查：
   - 只能存在一組 AUTO_PROGRESS_START/END
   - 檔案中不得再出現第二份「專案總完成度」口徑
3) 檢查最新 audit 檔是否生成：
   - runtime/handoff/state/PROJECT_BOARD_CANONICAL_TASK_AUDIT_*.md
4) 等待下一次 pm_tick（或手動執行 scripts/pm_refresh_board_canonical.sh pm_tick）：
   - stdout log 應持續穩定輸出同一口徑（total/done 不應跳動）
5) 若發現 total/done 在未改動 board 的情況下跳動：
   - 代表仍有舊腳本在寫入或 board 仍殘留第二套進度區塊
   - 必須先停下主線任務，先完成 §3 的殘留清理收斂

## 6. 變更規則（Patch-only）
任何修改本 Bible 或 canonical 規則：
- 只能用 v1.x patch
- 必須附 sha256 sidecar
- 必須先產出一次「前後對照 audit」證據
