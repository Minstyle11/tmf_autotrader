# NEW WINDOW AUTOSTART (ULTRA / OFFICIAL-LOCKED) — ATTACHMENT-ONLY CONTRACT
Generated: 2026-02-01 15:07:49

## 0) 你現在看到「最新 ULTRA WindowPack ZIP + sha256」被附在訊息上，但使用者**沒有打任何文字**
這是**正常流程**（Zero-Text Handoff）。
你的任務是：**像同一個視窗續跑**，不反問，不重新探索，直接依 One-Truth 繼續。

---

## 1) One-Truth / Single Source of Truth
- 唯一事實來源：使用者附上的 `TMF_AutoTrader_WindowPack_ULTRA_*.zip` + `.sha256.txt`
- ZIP 內已封存（Hard-REQ）：
  1) Opening Prompt FINAL
  2) HANDOFF SOP Bible
  3) Env Rebuild HardGate evidence
  4) OneShot HardGate SOP / Script
  5) next_step（下一步主線）

---

## 2) 你在新視窗必做的固定順序（不得跳步）
### 2.1 先做 OneShot HardGate（pack + env）
請在回覆中**直接給出**下面這個 Terminal 指令，並要求使用者貼回輸出：
- `cd ~/tmf_autotrader && bash scripts/ops_new_window_oneshot_hardgate_v1.sh`

### 2.2 OneShot HardGate PASS 後：無縫續跑
HardGate PASS 後，你必須：
1) 讀取：`runtime/handoff/state/next_step.txt`
2) 依 next_step 的內容，給出「下一個唯一 Terminal 指令」（一回合一指令）
3) 嚴格延續 OFFICIAL-LOCKED / v18 One-Truth / 既有不可更動鏈路的紅線規則

---

## 3) 失敗處理（只能走這條）
- 若 OneShot HardGate FAIL：你必須停在驗收/除錯，不得往下開發。
- 若附件/ZIP 無法讀取：請要求使用者改貼 `runtime/handoff/state/NEW_WINDOW_CLIPBOARD_ULTRA_ZH.txt` 內容（Emergency Fallback）。

---

## 4) 禁止事項（為了 100% 無縫接軌）
- 不得要求使用者「另外貼開場白」；開場白已封存於 ZIP。
- 不得修改 OFFICIAL-LOCKED v18 的任何 red-line 鏈路。
- 不得一次給多個 Terminal 指令。
