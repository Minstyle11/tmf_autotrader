# PROJECT_BOARD AutoSync Bible v1 (OFFICIAL-LOCKED)

- Updated: 2026-02-19 16:06:28
- Scope: `docs/board/PROJECT_BOARD.md` progress consistency, anti-jump, single-writer discipline
- Status: **HARDGATE PASS evidence exists in terminal logs** (stable reruns + single markers + TASK truth == canonical)

---

## 0) One-Truth 原則（最重要）

**PROJECT_BOARD 的「任務真相源」= 只看 `- [ ] [TASK:...]` / `- [x] [TASK:...]` 這類 TASK checkbox。**

- 任何「非 TASK checkbox」（例如里程碑段落、描述段落）不得被 progress 計算當成任務。
- 若歷史上存在非 TASK checkbox，必須先「遷移成 TASK」後再計算進度（你已完成 TASK migration，並且 hardgate 已驗證一致）。

> 結論：**board 進度永遠由 TASK checkbox 推導**，其餘文字/legend/說明不得影響計算。

---

## 1) 單一寫入者（Single Writer）鐵則

**只有一條 canonical chain 允許改寫 board 的 progress blocks：**

- Canonical entrypoint（LaunchAgent / 人工手動都要走這條）：
  - `scripts/pm_refresh_board_canonical.sh`
- Canonical writer：
  - `scripts/pm_refresh_board_v2.py`

說明：
- `pm_refresh_board_canonical.sh` 具備 single-instance lock（atomic mkdir）。
- `pm_refresh_board_v2.py` 會更新 board 的兩個 blocks（AUTO_PROGRESS 與 AUTO:PROGRESS），並輸出唯一穩定的一行 log：
  - `[OK] canonical board progress: ...`

---

## 2) Marker 單一化規範（避免重複 blocks 導致進度亂跳）

board 內以下 markers **必須各只有 1 組**：

- `<!-- AUTO_PROGRESS_START -->` / `<!-- AUTO_PROGRESS_END -->`
- `<!-- AUTO:PROGRESS_BEGIN -->` / `<!-- AUTO:PROGRESS_END -->`

HardGate 規範：
- marker count 必須全部等於 1
- 任一 marker count != 1 → 視為 **board 不一致（不可打包、不可交接）**

---

## 3) HardGate（一致性闖關）規範（每次要能自證）

每次要宣告「board autosync OK」前，必須同時滿足：

1) `pm_refresh_board_v2.py` 連跑三次輸出完全一致（total/done/doing/blocked/pct）
2) marker count 全部為 1
3) TASK hits 計數與 canonical block 計數完全一致（total/done/doing/blocked/todo）

> 你已在本視窗達成：`[PASS] board autosync consistency HARDGATE OK (stable + single markers + TASK truth matches canonical)`

---

## 4) 壞掉時的處置原則（先救一致性，再談進度）

若未來再出現任何以下症狀：
- 進度突然跳到 0/0
- pct 與 done/total 對不上
- marker count > 1
- TASK hits 與 canonical 不一致

處置順序（不得省略）：
1) 先停止「任何可能寫 board 的排程」造成的連鎖寫入（保持 single-writer）
2) 恢復 board 到最後一份已知良好的 `.bak_*`
3) 以「TASK truth」重新 rebuild SINGLE header+blocks
4) 重新跑 HardGate（3 次穩定 + marker=1 + TASK==canonical）

---

## 5) 新視窗強制聚焦主線推進（治理條款）

- 新視窗若要開發主線任務：
  - **先確認 board autosync HARDGATE OK**
  - 再開始做任何主線任務，避免進度漂移再次發生
- Ultra Pack 前置條件：
  - 必須附上本文件（本 Bible + sha256）
  - 必須附上「board autosync HARDGATE PASS」的證據（終端輸出或報告）

---

## 6) Acceptance Steps（逐步）

1. `python3 scripts/pm_refresh_board_v2.py` 連跑 3 次 → 三次輸出一致
2. 檢查 `docs/board/PROJECT_BOARD.md` 內 marker count 全部為 1
3. 檢查 TASK hits 與 canonical block 計數一致
4. 以上三項 PASS → 才允許進行 Ultra Pack / 新視窗交接
