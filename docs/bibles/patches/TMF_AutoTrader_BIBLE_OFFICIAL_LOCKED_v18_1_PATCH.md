# TMF AutoTrader OFFICIAL PATCH（v18.1）— 統計嚴謹性 × 在地交易所硬約束 × 自主學習安全護欄（One-Truth 延伸）

**日期**：2026-02-04（Asia/Taipei）
**Patch 目標**：在不破壞 v18 主體架構的前提下，補上「量化系統最常被忽略、但會在真實上線直接毀滅期望值」的三塊：
1) **回測/研究的統計嚴謹性終極護欄**（防 data snooping、backtest overfitting、Sharpe 膨脹）
2) **TAIFEX 在地“硬限制”前置驗證**（避免 Rejected/錯單/交易所保護機制踩雷）
3) **自動學習/自我改進的安全治理**（drift/非平穩/線上學習 = 必須“可控、可回退、可凍結”）

> **使用方式**：v18 仍是 One-Doc/One-Truth。此檔是 **v18.1 Patch**：
> - 主線助理在開發/設計/驗收時，視為與 v18 同等級硬規則。
> - 任何衝突：以 v18.1 補丁為準（因為它是針對 v18 的缺口補強）。
> - 若你要把補丁「合併回 v18」，請在 v18 指定章節插入下列段落即可。

---

## A) 研究/回測：統計嚴謹性「硬闖關」補強（必做）

### A1) v18 原本的 Research Gate 再加一層：**DSR / PBO / Reality Check**
**問題本質**：只要你測的策略/參數夠多，總會“找到”看起來很強的結果，但那可能只是運氣。
因此 v18 的研究闖關必須新增以下三個“硬闖關”：

1) **Deflated Sharpe Ratio（DSR）**：校正多重測試 + 非常態分布導致的 Sharpe 膨脹。
2) **Probability of Backtest Overfitting（PBO, CSCV）**：估計你的 backtest 有多大機率是過度擬合。
3) **White’s Reality Check / Hansen SPA（Superior Predictive Ability）**：對多策略/多規則做聯合檢定，控制 data snooping。

依據：
- Bailey 等人對 DSR 與 PBO 的系列工作（含 DSR 與 PBO/CSCV）。
- White (2000) 對 data snooping 的 Reality Check。

（這些不是學術潔癖，是真正能把「樣本內神作」變成「上線活得下去」的最低門檻。）

**v18.1 Research Gate（新增硬門檻）**
- 任何候選策略要進入 paper/live，除了 v18 原本的 walk-forward / purged CV / bootstrap 之外，還要同時滿足：
  - **PBO ≤ 0.1**（更嚴格可用 0.05）
  - **DSR ≥ 門檻**（建議：≥ 1.0 的對應顯著性，或等價的 p-value ≤ 0.05）
  - Reality Check / SPA：整體 p-value 通過（避免你只是挑到一個幸運規則）

> 若你現在還沒有現成 runner：先做「最小可用版本」：
> - DSR/PBO 先用 Bailey 的公開實作/公式寫成 `research/stat_gate_v1.py`。
> - Reality Check 先用 block bootstrap（同日/同週 block）對多策略的超額報酬做 joint test。

### A2) 研究輸出改成「三件套」才能進下一關
每個策略候選（含參數集）必須輸出：
- `MODEL_CARD.md`（策略=模型，列出假設、特徵、交易成本、失效情境、版本、資料窗）
- `STAT_GATE_REPORT.md`（DSR/PBO/RealityCheck + 報告 hash）
- `REPLAY_SEED.yaml`（可重現：資料切分、隨機種子、版本、commit hash、成本模型版本）

這會直接提升「可回放、可稽核、可迭代」能力，避免未來“策略變好/變差卻說不清原因”。

---

## B) TAIFEX 在地交易所硬限制：必做的「送單前」驗證（避免 Rejected / 錯單）

### B1) Order Size Limits（最容易踩雷）
TAIFEX 對不同委託型態有每筆口數上限；尤其 **Market order 在日盤與夜盤上限不同**。送單前必須檢查。
- Market order：日盤每筆最多 10 口；夜盤每筆最多 5 口。
- Limit / MWP 等亦有上限（商品別不同）。

=> v18 的 OrderGuard 必須把 **TAIFEX order-size-limit 規則**做成「硬擋」：超過就拆單或拒單（依 policy）。

### B2) MWP（Market with Protection）一定要用“交易所定義”
MWP 不是你以為的“加幾點保護”就結束：交易所會將 MWP 轉成限價，價格由**最佳 bid/ask ± protection points**轉換。
=> 你的滑價/成交概率/拒單風險評估，必須按交易所定義建模；不能只用“理想化市價單”。

### B3) Price limit / dynamic mechanisms：要把“交易所保護”當成 regime
TAIFEX 不同商品可能存在多層級 price limit、動態穩定措施等。
=> v18 的 Regime Engine（或 market regime）必須把「靠近漲跌停/擴大/動態機制觸發」當成**禁做或降風險模式**，至少做到：
- 觸及/逼近保護機制：下調 size、縮短持有、只允許平倉、或直接停機（依 policy）。

---

## C) Shioaji / 永豐金：事件真相源的「更嚴格」落地規則

### C1) Deal 事件可能先於 Order 事件（必須容忍 out-of-order）
Shioaji 明確說明：你“可能”會先收到 deal event 再收到 order event（交易所訊息優先權導致）。
=> v18 的 Event Sourcing 必須保證：
- 事件處理器是 **可亂序、可重複、可補齊** 的（idempotent + upsert）。
- 不能假設「order event 一定先到」。

### C2) subscribe_trade 必須視為“可關閉但不建議”
Shioaji 提到可以不訂閱 trade event（subscribe_trade=False），但對自動化交易系統來說，這會破壞“真相源”。
=> v18.1：除非是 research-only sandbox，否則 **強制 subscribe_trade=True**。

---

## D) 自主學習/自我改進：加上「安全護欄」才能准許進 live

### D1) “學習”只能在三種模式中切換（硬規則）
1) **Frozen（凍結）**：live 預設；只用已驗證權重/參數，不在線更新。
2) **Shadow（影子）**：線上學習只產生建議，不影響下單；輸出 drift/收益差異報告。
3) **Promote（升級）**：只能在 release window 以 canary 提升（帶 rollback）。

=> 沒有這三段式，你的“自主學習”會變成“自主爆炸”。

### D2) Drift 必須先被量化：Concept drift detector + 失效處置
金融市場非平穩是常態。你要做的是：
- drift 檢測（統計/模型型），
- drift 觸發後的策略凍結/降級/切換，
- 並且寫入 Finance Close Pack 與 Postmortem。

可參考：概念漂移在金融時間序列的研究脈絡；以及近年針對 drift 的 RL 框架工作（不代表可直接上線，但提醒你 drift = first-class problem）。

### D3) Safe RL / Risk-aware bandits：只允許“有約束”的學習
如果你要把策略選擇/資本配置變成 bandit/RL：
- 必須採用 **風險約束**（如 CVaR/mean-variance constraints）或安全 RL 的 constraint formulation。
- 在 live 中，學習器只能決定「在風險預算內怎麼分配」，不能越過風險引擎。

---

## E) 事故文化補強：交易系統 = SRE 系統

### E1) 強制 Blameless Postmortem（但要“可執行改進”）
每一次嚴重異常（停機、錯單、對帳失敗、DPB 觸發、連續退單、資料延遲超標）都要產出 postmortem：
- 影響、時間線、根因、修復、行動項（含 owner + deadline）
- 不責備個人，專注系統性修復與降低復發率。

---

## F) v18.1 最小落地工作清單（主線助理拿來做 Roadmap 切片）

1) `research/stat_gate_v1.py`：DSR + PBO（CSCV） + 最小 RC/SPA（block bootstrap）
2) `core/orderguard_taifex_v1.py`：market order size limits / MWP 定義 / per-product caps
3) `core/event_store_idempotent_v1.py`：亂序/重放/去重/補齊（deal-before-order OK）
4) `ops/learning_modes_v1.md`：Frozen/Shadow/Promote + canary + rollback
5) `ops/drift_detector_v1.py`：最小 drift 指標（分布差、收益差、滑價/成交率劣化）+ 觸發策略凍結
6) `ops/postmortem_template.md`：SRE 事故模板 + 自動生成 Finance Close Pack 附錄

---

## 驗收步驟（逐步）/ Acceptance Steps

### [A] 統計嚴謹性 Gate（DSR/PBO/RealityCheck）
1. 在 `research/` 新增 `stat_gate_v1.py`，輸入為：策略績效序列（或每日/每筆 returns）+ 多策略集合。
2. 產出 `STAT_GATE_REPORT.md`：包含 DSR、PBO、RC/SPA 的結果與門檻判定（PASS/FAIL）。
3. 隨便抽 3 個已知“看起來很強但其實是參數調出來”的策略：應 FAIL（PBO 高或 RC 不過）。
4. 抽 1 個你認為穩的策略：至少 PBO 不高（≤0.1），且 DSR 不被打回原形。
5. 把報告 SHA256 寫入 Finance Close Pack 的 research section。

### [B] TAIFEX OrderGuard（硬擋）
1. 在紙上列出你會下的 order types（Market / Limit / MWP）。
2. 實作檢查：若 market 且日盤 size>10 → 拆單或拒單；夜盤 size>5 → 拆單或拒單。
3. 模擬送單：用 unit test 驗證拆單口數與數量守恒。
4. 若使用 MWP：驗證價格轉換邏輯與保護點設定（至少能在 log 中看到 bid/ask、保護點、轉換後限價）。
5. 產出 `ORDERGUARD_SELFTEST.md` 並寫入 hash。

### [C] Shioaji 事件亂序容忍
1. 寫一個測試 harness：先喂一個 deal event，再喂對應 order event。
2. 確認 position / fills / order state 最終一致。
3. 反向（order→deal）也一致。
4. 重複喂相同事件 2 次，狀態不應變壞（idempotent）。

### [D] Learning modes（Frozen/Shadow/Promote）
1. 預設啟動 Frozen：任何 online update 都被拒絕。
2. 切到 Shadow：學習器產生建議，但下單邏輯不採用；對比報告落盤。
3. Promote：只能在 release window，且 must canary；若 drift/風險觸發 → 自動 rollback 回 Frozen。

### [E] Postmortem
1. 人為製造一次 “行情資料延遲 > 門檻” 事件。
2. 系統應自動降級/停機（依 v18 policy），並產出 `POSTMORTEM_*.md`。
3. 模板必含：timeline、root cause、action items。
4. Finance Close Pack 必包含此事件摘要與 hash。

---

## Patch 引用（主線助理使用的“外部真相錨點”）
- DSR / PBO（Bailey & López de Prado）
- White (2000) Reality Check for Data Snooping
- TAIFEX Order Size Limits、Order Types（MWP）
- Shioaji Futures order/deal event 文檔（deal event may arrive sooner）
- Google SRE Postmortem culture（blameless, actionable）
