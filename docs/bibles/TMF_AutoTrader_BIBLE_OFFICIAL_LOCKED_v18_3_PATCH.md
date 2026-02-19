# TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18.3_PATCH
> 本文件為 v18 的「補強 Patch」。主線仍以 v18 為 One-Doc/One-Truth；本 Patch 僅做增補/澄清，不破壞既有治理。
> 版本：v18.3（Generated: 2026-02-18 20:27:09）

---

## 1) Execution Safety：交易所硬限制（TAIFEX）送單前必做 Preflight（不可繞過）
### 1.1 市價單（MKT）口數硬上限（必遵守）
- Regular session：每筆 **≤ 10** 口
- After-hours session：每筆 **≤ 5** 口
- 若策略/執行要求 qty > limit：**必須拆單（SPLIT）** 或 REJECT；不得硬送導致交易所拒單（Rejected）造成不可控成本與狀態漂移。

### 1.2 MWP（Market with Protection）必須使用「交易所定義」的轉限價邏輯
- MWP 送出時不填 price；交易所收到後會依「同邊最佳價 ± 保護點數」轉成限價單：
  - Buy：best bid + protection points
  - Sell：best offer - protection points
- 因此執行層在產生/驗證 MWP 時，必須具備：
  1) `best_same_side_limit`（同邊最佳限價）
  2) `protection_points`（依商品/交易所表定）

---

## 2) Market Calendar Gate：休市/非交易時段一律拒單（預設），只允許「測試白名單」繞過
### 2.1 預設規則（LIVE/PAPER 一視同仁）
- 若市場休市（例：春節連假）→ `EXEC_MARKET_CLOSED` → `REJECT (HIGH)`
- 該 gate 必須在「實際送到 broker/OMS」之前發生（pre-trade）。

### 2.2 測試繞過（僅限本機/回歸測試）
- 僅在回歸/單元測試允許 `meta.allow_market_closed=true` 作為白名單繞過。
- **嚴禁**在任何 live runner / 自動交易主程式中預設打開此開關（否則等同禁用交易日治理）。

---

## 3) SPLIT 證據鏈：必須寫入 Parent Row + Children Row（可回放/可對帳）
### 3.1 必須落庫的最小證據
- Parent row（status=`SPLIT_SUBMITTED`）：
  - `broker_order_id = split_parent_id`
  - `action = SPLIT`
  - meta 至少包含：`split_limit`, `split_requested_qty`, `split_children`（子單回應摘要）
- Children row（status=`SUBMITTED` or equivalent）：
  - meta 必須包含：`split_parent_id`, `split_index`

### 3.2 原則
- Audit/落庫失敗 **不可**中斷下單流程（audit must not break execution path）。
- 但 audit 必須有「可觀測」的失敗訊號（例如 ops log / diag counter）— 後續 M8/M9 再落地。

---

## 4) Risk Engine 介面相容層（不得因版本差異讓下單路徑爆炸）
- Wrapper 呼叫 `risk.check_pre_trade(...)` 時，必須允許：
  - 新版：接受 `entry_price=` keyword
  - 舊版：不接受該 keyword（fallback 走 positional 或 `price=`）
- 規則：**相容層只能在 wrapper 內做**，不得把「版本差異」擴散到策略層。

---

## 5) 本 Patch 對應落地檔案（Evidence）
- execution/taifex_preflight_v1.py：effective price type + market qty limit + MWP validation
- execution/reject_policy.yaml：新增 EXEC_MARKET_CLOSED mapping
- execution/tw_market_calendar_v1.py + execution/tw_market_holidays_2026.json：交易日 gate
- src/oms/paper_oms_risk_safety_wrapper_v1.py：
  - market calendar gate
  - SPLIT parent row insert + children linkage
  - risk.check_pre_trade interface compatibility
