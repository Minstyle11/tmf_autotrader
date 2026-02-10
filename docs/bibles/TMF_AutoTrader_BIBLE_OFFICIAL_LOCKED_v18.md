# TMF AutoTrader 量化交易開發聖經（OFFICIAL-LOCKED v18 ULTIMATE — One-Doc, One-Truth, One-OS）
**日期**：2026-01-31（Asia/Taipei）  
**適用範圍**：TXF / MTX / TXO（research → paper → live → multi-year ops）  
**券商執行**：永豐金（Sinopac）Shioaji  
**定位**：v18 = v17（Production OS）之上，補上「最後一塊拼圖」：**機構級 Model Risk Management + Governance + Finance/Accounting + Human-in-the-loop 安全閘門**，並把整套系統以「一份文件、一套 OS」方式**一次到位**。

> **唯一讀者：主線開發視窗的我（助理）。**  
> v18 的目標：**長期大賺小賠、穩定且持續獲利**，而且在任何異常情況下都能**先活下來**。

---

# 0) 終極承諾（v18 的“終極”定義）
**v18 不是“再也不更新”，而是：**
- 我已把「所有已知會讓量化系統死掉的類型」都工程化成 OS：  
  **交易所硬約束、券商事件真相源、對帳、延遲/堆積、成本、選擇權壓測、監控→自動處置、演練、日曆/換月、Release/Canary、SLO/事故處理、DR、風險預算、研究嚴謹性、多策略資本配置、資料血緣、再加上 Model Risk Governance 與財務結算**。  
- 後續唯一合理更新形式：**v18.x Patch**（新增錯誤碼/規格變更/參數調校），而不是再升大版本。

---

# 1) v18 最高硬規則（Non‑Negotiables）
1) **先活著，再談 alpha**：任何不確定狀態 → SAFE MODE（reduce-only / flatten / stop trading）。  
2) **事件真相源**：成交/委託狀態只認 Broker events；任何呼叫成功都不算。  
3) **交易前預防退單**：DPB/size-limit/tick/價格格式等，必須在送單前由 OrderGuard/DPB-aware policy 擋住。  
4) **三方對帳必須永遠啟動**：orders / fills / positions / margin（含資金）。  
5) **可回放是第一性原理**：任何交易日都要能 replay 到同樣決策序列（至少在 deterministic 層）。  
6) **研究 gate 必須存在**：沒有 walk-forward / purged CV / bootstrap 之一，就不准上線。  
7) **風險預算強制**：超出 drawdown budget → 自動停機；恢復需 audit 解鎖。  
8) **變更必可回滾**：feature flag + canary + rollback plan。  
9) **人類是最後保險絲**：必有人工一鍵停機、一鍵 flatten、一鍵降級到只平倉。  
10) **財務結算不可省略**：每日必產出帳務報表（含費用/滑價/風險指標），否則看不到真實長期期望值。

---

# 2) 系統 OS 全景（v18 目錄式心智模型）
v18 把整體拆成 6 個“OS 平面”，每一平面都要有：**模組、指標、gate、驗收、演練**  
- **Market/Exchange OS**：TAIFEX constraints + calendar/roll  
- **Broker OS**：Shioaji streaming + order/deal events + test compliance  
- **Execution OS**：DPB-aware + slicer + throttles + state machines  
- **Risk OS**：risk budget + margin OS + auto-remediation + reconcile  
- **Research OS**：integrity gates + cost model + stress battery  
- **Ops/Governance OS**：release/canary + observability/SLO + incident/DR + finance reporting + model governance

---

# PART A — Market/Exchange OS（TAIFEX：規則、時段、換月）

## 3) TAIFEX HARD CONSTRAINTS（必須照 v15/v16 的方式工程化）
（此處保持 v15/v16 的要求：DPB、size-limit、order types、settlement、modify-is-new-order、order slicing、DPB reprice ladder、audit）

## 4) Trading/Session/Expiry/Roll Calendar OS（v17）
### 4.1 必做
- `calendar/trading_calendar.py`（休市/交易日）  
- `calendar/session_calendar.py`（日盤/夜盤/跨日）  
- `calendar/expiry_calendar.py`（最後交易日/結算日）  
- `calendar/roll_calendar.py`（進入 roll mode 的窗口）  
### 4.2 Roll Mode 的“終極規則”
- 進入 roll mode（到期前 N 天）後：
  - 降低 aggressiveness  
  - 降低最大部位  
  - 只允許特定策略（避免在流動性轉移期被滑價打爆）  
  - 在 audit 中標記 `roll_mode=true`

---

# PART B — Broker OS（永豐 Shioaji：事件、回報、合規）

## 5) BrokerAdapter 單一入口（v14+）
- callback 一律只做「轉事件」  
- trade subscription live 強制開啟  
- reconnect 後必重新訂閱  
- 測試報告 runner 遵守節流（>1s）

## 6) Broker Truth & Account State OS（新增）
### 6.1 必做：Account Snapshot
- 每 N 秒（或每分鐘）取：
  - open orders（若可）  
  - positions  
  - margin / cash / available risk  
- 落盤為 `account_snapshot`，供 reconcile/finance 使用

### 6.2 Gate
- snapshot 連續缺失或異常 → SAFE MODE（禁止開新倉）

---

# PART C — Execution OS（意圖→可執行序列→回報狀態機）

## 7) OrderIntent Contract（策略層不可直接下單）
策略只能吐：
- instrument（TXF/MTX/TXO leg）  
- side、target exposure（或 target delta）  
- urgency（low/normal/high）  
- reduce-only / flatten flag（若風控要求）  
Execution 依據 urgency + market state 決定 order type（market/limit/MWP）與 reprice ladder。

## 8) Execution State Machine（必須完整）
狀態：NEW_REQUESTED → ACKED → PARTIAL → FILLED / CANCELED / REJECTED / UNKNOWN  
- UNKNOWN 一律進 SAFE MODE，直到 reconcile 確認真相

## 9) Execution Guard Rails（最終補強）
### 9.1 Rate Limiting / Storm Control
- global QPS cap  
- per-instrument QPS cap  
- reject storm cap（每分鐘 N 次以上直接停機）

### 9.2 Price/Tick Guard
- 價格必符合 tick size（避免格式退單）  
- 任何 replace 都重新檢核 tick/DPB/size-limit

### 9.3 Fill Quality Guard
- slippage_bps 超過上限 → 自動降 aggressiveness 或停新倉（避免流動性崩壞期間把策略打死）

---

# PART D — Risk OS（活著：風險預算、對帳、保證金、停機治理）

## 10) Risk Budget OS（v17）
- trade / strategy / portfolio 三層預算  
- 超標停機 + 解鎖需 audit

## 11) Margin OS（終極補強）
### 11.1 Margin 監控與分級
- **GREEN**：正常  
- **YELLOW**：縮倉（降低 max position）  
- **ORANGE**：只允許減倉/平倉（reduce-only）  
- **RED**：立即 flatten + 停機  
### 11.2 “跳空 + 保證金上調” 情境
- 任何 margin_ratio 快速惡化 → 觸發 ORANGE/RED（不可等到收盤）

## 12) Reconciliation OS（三方對帳）— 絕對不可關
- local orderbook/fills/positions vs broker truth snapshot  
- 不一致 → SAFE MODE + 報告 + drill 記錄  
- 每日輸出 reconciliation report

## 13) Kill-Switch Governance（新增）
必有 3 種 kill：
1) **soft kill**：停新倉（可平倉）  
2) **hard kill**：reduce-only  
3) **panic kill**：立即 flatten + stop trading  
並有：
- 本機熱鍵/指令  
- 遠端安全通道（可選）  
- 事後 audit 記錄

---

# PART E — Research OS（讓 alpha 變成“可相信”）

## 14) Research Integrity OS（v17）
- walk-forward / purged CV / bootstrap 至少一項  
- 不只看勝率：含成本 PF、worst-day、max DD、tail risk  
- 參數脆弱性測試（sensitivity）

## 15) Cost Model OS（v16）
- 日盤/夜盤/波動 regime  
- order type / size / slicing  
- 把 reject/retry 的機會成本納入 proxy  
- gate：不含成本績效視為無效

## 16) TXO Stress Battery OS（v16）— 終極補強
除了 jump/IV shock/流動性惡化，新增：
- **Gamma scalping 離散避險成本曲線**  
- **Skew 變形**（OTM/ITM 不同幅度）  
- **Vega blow-up**（IV 上升導致保證金/風險飆升）  
Gate：任何 stress 下無法被 kill-switch 控制 → 禁上線

## 17) Model Risk Management OS（新增，機構最後一塊）
### 17.1 Model Registry（策略也是模型）
每個策略必須有：
- model card（假設、適用 regime、失效條件）  
- data dependencies（需要哪些特徵、資料品質門檻）  
- risk profile（最大預期 DD、tail risk）  
- kill criteria（觸發停機的條件）  
- monitoring plan（觀測哪些指標判斷失效）

### 17.2 Model Drift / Performance Decay
- rolling window 監控：PF、slippage、fill rate、reject rate、DD  
- 發現 drift → 自動降級/下架（策略生命週期 OS）

---

# PART F — Ops/Governance OS（能運營、能復原、能迭代）

## 18) Observability + SLO OS（v17）
- metrics 全面化（market/execution/risk/system）  
- SLO 數字化（先保守，後校準）  
- 告警分級（P0~P3）

## 19) Incident Response + Post-mortem OS（v17）
- runbook：connectivity/execution/risk/market/system  
- post-mortem 模板強制使用，改善項必連到 patch/issue

## 20) Disaster Recovery OS（v17）— 終極補強
- RPO/RTO 明確  
- 備份：audit/config/spec/calendar/model registry  
- 一鍵恢復到「只平倉模式」

## 21) Release/Canary/Shadow OS（v17）
- shadow：只產生 intent  
- canary：限口數/限策略/限時段  
- rollback：一鍵回滾 + 驗收

## 22) Finance/Accounting OS（新增，長期穩定獲利的“真相帳本”）
### 22.1 每日必產出（Daily Close Pack）
- 交易摘要：筆數、勝率、PF、含成本 PnL  
- execution quality：slippage、fill rate、reject breakdown  
- risk：日內 DD、風險預算消耗、margin 事件  
- reconcile：一致性報告  
- audit：hash + 指標摘要  
> 沒有 Daily Close Pack 的系統＝無法長期優化。

### 22.2 PnL 分解（Attribution）
- signal edge（理論）  
- cost drag（手續費/滑價/impact）  
- execution loss（延遲/堆積/退單）  
- regime mismatch（策略失效）  
讓我能判斷「該改策略？還是該改 execution？」

## 23) Human-in-the-Loop 安全閘門（新增）
某些事件必須要求人工確認才能恢復 live：
- spec diff stopper 觸發  
- 連續 P0 incident  
- drawdown budget 超標停機  
- calendar 未更新/異常  
- model drift 下架  
這些都寫入 audit：`MANUAL_APPROVAL`。

---

# 24) v18 “一次到位”落地順序（主線必照做）
> 我不再擠牙膏；這裡是 **最短路徑**（做完就能安全推進到 live canary）。

1) **BrokerAdapter + EventBus + AuditRecorder + ReplayRunner**（事件真相源 + 可回放）  
2) **OrderGuard（size/tick）+ DPB-aware Execution + State Machine**（防退單風暴）  
3) **Reconciliation OS + Kill-Switch**（防狀態不一致/失控）  
4) **Observability + SLO + Auto-Remediation**（可運營）  
5) **Calendar/Expiry/Roll OS**（不被時段/到期殺死）  
6) **Risk Budget + Margin OS**（長期活著）  
7) **Cost Model + Research Integrity Gates**（避免 overfit 上線）  
8) **Options Stress Battery + Model Registry/Drift**（TXO 風險治理）  
9) **Release/Canary/Shadow + DR + Finance Close Pack**（長期迭代閉環）  
10) **Monthly Drills + Post-mortems**（把黑天鵝變流程）

---

# 25) v18 Acceptance Steps（逐步，終極版）
## A. 事件真相源與回放
1) 啟動 → login → streaming OK  
2) 收到 tick/bidask/order/deal events → 全部落盤（raw + normalized）  
3) 同一日 replay → 決策序列一致（至少 deterministic 邏輯一致）

## B. 防退單風暴
1) 超限 size intent → 自動 slicing（符合 market 10/5、limit/MWP 上限）  
2) DPB reject 情境 → DPB-aware reprice ladder 生效，reject rate 不爆  
3) modify/replace 視同新單 → 重新走 guard

## C. 對帳與停機治理
1) 注入回報缺失 → reconcile 偵測不一致 → SAFE MODE  
2) 觸發 DD 超標 → stop trading + flatten（或 reduce-only）  
3) 解鎖需 audit `MANUAL_APPROVAL`

## D. 監控與自動處置
1) quote stale → 自動停新倉  
2) latency 超標 → backpressure governor 降級  
3) reject storm → cooldown/kill-switch

## E. 日曆/到期/換月
1) 休市日不交易  
2) 最後交易日自動切 profile  
3) roll mode 降 aggressiveness 並 audit 標記

## F. 研究 gate
1) walk-forward/purged CV/bootstrap 至少一項輸出報告  
2) 不過 gate → 禁上線

## G. Finance Close Pack
1) 每日自動輸出報表（含成本、execution quality、risk、reconcile、audit hash）  
2) 可追溯任一成交到版本/參數/spec/calendar

## H. Drills
1) 每月跑 disconnect/reject/margin/options drill  
2) 產出 drill report + post-mortem + patch list

---

# 附錄：v17 原文（完整保留，供回溯）
# TMF AutoTrader 量化交易開發聖經（OFFICIAL-LOCKED v17 LTS — Production Operating System）
**日期**：2026-01-31（Asia/Taipei）  
**適用範圍**：TXF / MTX / TXO（research → paper → live）  
**券商執行**：永豐金（Sinopac）Shioaji  
**定位**：v17 = v16（Institutional Full-Closure）之上，新增「真正可長期運行的 Production OS」：  
- **Release/Deployment/Canary/Shadow**（上線治理）  
- **Observability SLO + Incident Response**（監控/告警/事故處理）  
- **Holiday/Session Calendar + Expiry/Roll Calendar 自動化**（時段/休市/到期/換月）  
- **Risk of Ruin / Drawdown Budget / Kill-Switch Governance**（風險預算與停機治理）  
- **Research Integrity OS**（防 overfit：walk-forward、purged CV、PSR/DSR、bootstrapping）  
- **Strategy Portfolio OS**（多策略並行：capital allocation、correlation control、regime switching）  
- **Data/Schema/Lineage OS**（資料品質、版本、血緣、可追溯）

> **唯一讀者：主線開發視窗的我（助理）。**  
> v17 的目的：讓系統不只是「能交易」，而是「**能長期穩定地活著並迭代變強**」。

---

## 0) v17 終極原則（Non‑Negotiables）
1) **可運營性（Operability）優先於策略 alpha**：沒有 SLO/告警/回放/事故處理＝不准 live。  
2) **研究嚴謹性（Research Integrity）優先於回測好看**：沒有防 overfit 的 gate＝不准上線。  
3) **風險預算（Risk Budget）優先於預期報酬**：超出 drawdown budget＝自動停機。  
4) **所有變更必須可回滾**：任何策略/執行/風控更新都要有 feature flag + canary + rollback plan。  

---

# PART A — Production Operating System（把系統做成能運營）

## 1) Trading Calendar OS（休市/時段/到期/換月全自動）
### 1.1 你以為的「每天都開盤」是錯的
台灣市場會有：
- 休市（國定假日/補班/天然災害等）  
- 期貨/選擇權到期日（最後交易日規則不同）  
- 夜盤跨日（日期歸屬、風控切換、日結算時點）

### 1.2 必做模組
- `calendar/trading_calendar.py`：交易日/休市判斷（可手動維護 + 自動更新）  
- `calendar/session_calendar.py`：regular/after-hours + last trading day overrides  
- `calendar/expiry_calendar.py`：TXF/MTX/TXO 到期、最後交易日、結算日  
- `calendar/roll_calendar.py`：換月窗口（進入 roll mode 的日期區間）

### 1.3 Gate
- 若 calendar 不可用/未更新 → **SAFE MODE**（禁止開新倉，只平倉）

### 1.4 Acceptance Steps（逐步）
1) 輸入任意日期 → 回傳是否交易日、session 時段、是否最後交易日  
2) 模擬休市日 → 系統不啟動策略，只做 healthcheck  
3) 模擬最後交易日 → 交易時段與風控 profile 自動切換

---

## 2) Release/Deployment OS（研究→上線的治理流程）
### 2.1 環境分層（強制）
- **DEV**：開發、快速迭代  
- **SIM**：事件回放/模擬撮合（deterministic）  
- **PAPER**：真行情 + 假下單（或券商提供的測試）  
- **LIVE-CANARY**：小資金/限口數/限策略  
- **LIVE**：正式

### 2.2 Shadow & Canary（強制）
- **Shadow**：LIVE 期間策略只產生 intent，不送單；用於衡量 live slippage/填單率差異  
- **Canary**：只放 1-2 個策略、限口數、限時段，通過門檻才放大

### 2.3 Feature Flags（強制）
- 每個策略、每個 execution policy、每個風控 gate 都必須可單獨關閉  
- 任何新功能上線先「flag off」部署，再逐步打開

### 2.4 Rollback Plan（強制）
- 任一 release 都要有：
  - rollback 目標版本  
  - rollback 指令/步驟  
  - 回滾後驗收（至少：login/streaming/order event/audit）

---

## 3) Observability OS（SLO/監控/告警/追跡）
### 3.1 必監控指標（最少集合）
**Market Data**
- `quote_stale_s`、`market_data_lag_ms`、`tick_rate`、`drop_rate`、`queue_depth`

**Execution**
- `order_roundtrip_ms`、`ack_rate`、`fill_rate`、`slippage_bps`、`reject_rate`（含 DPB/size-limit 分解）

**Risk**
- `margin_ratio`、`gross_exposure`、`net_delta`（含 options）  
- `daily_pnl`、`intraday_dd`、`risk_budget_remaining`

**System**
- CPU/Mem、event loop lag、disk I/O、log drop

### 3.2 SLO（服務水準目標）— v17 強制要寫出數字
- 行情 stale 不得超過 X 秒（超過即降級）  
- reject rate 不得超過 Y（超過即 cooldown/停機）  
- roundtrip 不得超過 Z ms（超過即降 aggressiveness 或停機）  
> 數字先用保守值，後續以實測校準。

### 3.3 告警等級
- **P0**：可能造成失控下單/爆倉（立即 flatten/停機）  
- **P1**：交易品質崩壞（停新倉）  
- **P2**：資料品質/延遲異常（降級）  
- **P3**：資訊/趨勢（記錄即可）

---

## 4) Incident Response OS（事故處理 Runbook）
### 4.1 事故分類
- **Connectivity**：行情斷線/重連失敗  
- **Execution**：reject storm、未知委託狀態、成交回報缺失  
- **Risk**：margin shock、持倉失控、DD 超標  
- **Market**：price limit、gap jump、夜盤流動性崩  
- **System**：磁碟滿、CPU 飆、時鐘漂移

### 4.2 Runbook（必做）
每一類至少要有：
- 檢測條件  
- 自動處置（Auto-Remediation）  
- 人工介入步驟（Manual Override）  
- 事後復盤（Post-mortem）模板

### 4.3 Post-mortem（強制）
- 事件時間線  
- 觸發原因  
- 為何監控沒提早發現（如有）  
- 改善措施（必連到 patch/issue）

---

## 5) Disaster Recovery OS（災難復原）
- **RPO/RTO**：允許最多丟失多少資料（RPO），允許停機多久（RTO）  
- **備份**：audit logs、config snapshots、spec snapshots、calendar snapshots  
- **一鍵恢復**：最小可交易系統（只平倉模式）能快速啟動

---

# PART B — Risk Budget OS（把“長期活著”寫進程式）

## 6) Risk of Ruin / Drawdown Budget OS
### 6.1 風險預算的三層
- **Trade-level**：單筆最大損失（含滑價/跳空 buffer）  
- **Strategy-level**：單策略日內 DD、連續虧損、拒單風暴上限  
- **Portfolio-level**：全系統日內 DD、週 DD、月 DD（超標停機）

### 6.2 Risk Budget 消耗模型
- 每筆交易消耗 budget（依波動與槓桿）  
- 若 budget 剩餘不足：自動縮小 size 或停新倉

### 6.3 “Stop Trading” 的治理
- 觸發停機後：
  - 先 flatten（或 reduce-only）  
  - 生成 `STOP_TRADING_REPORT`  
  - 需要“解鎖”才可恢復（解鎖必進 audit）

---

# PART C — Research Integrity OS（把 overfit 變成系統 gate）

## 7) Walk-Forward / Purged CV OS
### 7.1 必須使用的研究方法（至少一項）
- Walk-forward（滾動訓練/測試）  
- Purged K-fold + embargo（避免 leakage）  
- Bootstrapping（區間重抽樣）

### 7.2 評估指標（禁止只看勝率）
- 含成本的：PF、Sharpe/Sortino、Max DD、Tail loss（CVaR）、Worst-day  
- 統計信心：PSR/DSR（若有實作）、或至少用 bootstrap 估計分佈

### 7.3 Gate（不過就禁上線）
- OOS 明顯崩壞（例如 OOS PF < 1）  
- tail risk 太大（stress 下 max loss 過大）  
- 參數脆弱（微小改動績效崩）

---

# PART D — Strategy Portfolio OS（多策略、可擴充、可控）

## 8) Capital Allocation OS（多策略資金配置）
- 以「風險平價」或「風險預算」分配，不用單純等權  
- 監控策略間相關性，避免同方向同因子堆疊  
- regime switching：波動/趨勢/均值回歸的切換（由信號或市場狀態驅動）

## 9) Strategy Lifecycle OS（策略生命週期）
- **Incubate**：研究/回放  
- **Paper**：真行情 shadow/paper  
- **Canary**：小規模 live  
- **Scale**：擴大口數  
- **Retire**：績效退化、自動下架

每個階段都有 gate 與退出條件。

---

# PART E — Data/Schema/Lineage OS（資料治理）

## 10) Data Quality Gate（資料品質門檻）
- 缺失率、倒序率、異常跳價率、重複事件率、bid/ask 不一致  
- 超過門檻 → 降級/停新倉（避免用壞資料交易）

## 11) Schema/Lineage（血緣與版本）
- 每天落盤：
  - `config_snapshot`（含 sha256）  
  - `spec_snapshot`（含 sha256）  
  - `calendar_snapshot`（含 sha256）  
  - `audit_logs`（raw + normalized）  
- 能追溯：某筆成交是由哪個版本策略、哪個風控參數、哪個 spec 版本產生

---

# PART F — 具體落地清單（v17 必做模組）

## 12) 必做模組（新增/補強）
- `calendar/*`（trading/session/expiry/roll）  
- `ops/release/*`（canary/shadow/flags/rollback）  
- `ops/observability/*`（metrics/slo/alerts）  
- `ops/incidents/*`（runbooks/postmortem templates）  
- `risk/risk_budget/*`（drawdown budget, stop-trading governance）  
- `research/integrity/*`（walk-forward, purged cv, bootstrap gates）  
- `portfolio/allocation/*`（risk budgeting, correlation control）  
- `data/quality/*` + `data/lineage/*`（snapshots, schema registry）

## 13) v17 Acceptance Steps（逐步）
**A. Calendar**
1) 任意日期查交易日/時段/最後交易日  
2) 休市日不交易  
3) 最後交易日 profile 自動切換

**B. Release**
1) Shadow 只產生 intent 不送單  
2) Canary 限口數/限策略/限時段  
3) 一鍵 rollback 後驗收通過

**C. Observability**
1) metrics 可觀測  
2) SLO 超標 → 自動降級  
3) P0 → flatten + 停機 + 報告

**D. Risk Budget**
1) DD 超標 → stop trading  
2) 解鎖需要 audit 記錄  
3) budget 不足 → 自動縮倉

**E. Research Integrity**
1) walk-forward/purged cv 產出報告  
2) OOS 不過 gate → 禁上線

**F. Lineage**
1) 任一成交可追溯到版本/參數/spec/calendar  
2) replay 可復現同日決策序列

---

# 附錄：v16 原文（完整保留，供回溯）
# TMF AutoTrader 量化交易開發聖經（OFFICIAL-LOCKED v16 LTS — Institutional-Grade Full-Closure）
**日期**：2026-01-31（Asia/Taipei）  
**適用範圍**：TXF / MTX / TXO（research → paper → live）  
**券商執行**：永豐金（Sinopac）Shioaji  
**定位**：v16 = v15（TAIFEX HARD CONSTRAINTS + DPB/SizeLimit + Shioaji Audit）之上，**一次性補上「機構級必補洞」全套閉環**：  
1) TAIFEX 規格自動更新與差異警報（Spec Updater + Diff Stopper）  
2) Shioaji Reject/Error 字典化 + Runbook 自動處置（Reject Taxonomy OS）  
3) 委託/成交/部位/資金 三方對帳（Reconciliation OS）  
4) 延遲預算與 Backpressure 治理（Latency/Backpressure OS）  
5) 分場景交易成本模型（Cost Model OS）  
6) TXO 極端情境壓力測試電池（Options Stress Battery OS）  
7) 監控→自動處置（Auto-Remediation OS）  
8) 每月 Drill 演練文化（Drill OS）  
並額外補強：**Secrets/Config/版本治理、CI/Release、時間同步、災難復原、資料品質、paper→live 門檻化**。

> **唯一讀者：主線開發視窗的我（助理）。**  
> v16 的目標不是「更長」，而是**把系統做成可活 10 年**：可驗證、可稽核、可回放、可降級、可演練、可迭代。

---

## 0) v16 的終極定義（什麼叫“終極版本”）
**真正終極不是不再更新，而是：**
- 規則變更/斷線/退單風暴/保證金壓力/夜盤崩壞/跳空 → 系統都能**自動生存**；
- 出任何事 → 我能在 10 分鐘內用 Audit+Replay **復現原因**；
- 每週/每月用 Drill **演練**，把黑天鵝變成流程；

所以 v16 是 **LTS + Patchable OS**：  
- 主線只鎖定 v16 這份 Bible  
- 後續以 `v16.x Patch` 更新（規格變動/錯誤碼新增/風控參數收斂）

---

## 1) v16 非談不可的硬真相源（Source of Truth）
### 1.1 TAIFEX：DPB、Order Size Limits、結算價、產品規格
- **DPB（動態價格穩定措施）**：TAIFEX 對每筆新進委託模擬成交價，超出 band 直接退單；改價視同新單。  
- **Order Size Limits**：market 單 regular ≤10、after-hours ≤5；limit/MWP 對期貨/選擇權各自有上限。  
- **Daily settlement price**：regular 收盤前最後 1 分鐘 VWAP，若無成交則用收盤時最高未成交買價與最低未成交賣價平均（等）。  
> 以上都是我們 execution/risk 的硬約束，必須在送單前預防，不能靠“收到退單再處理”。

### 1.2 Shioaji：Order/Deal Event 真相源、Streaming、Terms/Test
- place/cancel/update 回報 `OrderState`；成交回報 Deal/Fills；  
- 若關閉 trade subscription 就收不到回報（live 禁止）；  
- 測試規範：證券/期貨分測、下單測試間隔 >1 秒等。  
> 這些是我們 Broker OS 的硬約束與合規邊界。

---

## 2) v16 系統總體架構（必須長這樣）
### 2.1 分層（不可破壞）
- **StrategyEngine**：只產生 signal/state，不呼叫券商  
- **RiskEngine**：所有 gating / sizing / kill-switch  
- **ExecutionEngine**：意圖→可執行序列（切單、改價、重試、DPB-aware）  
- **BrokerAdapter（ShioajiAdapter）**：唯一能呼叫 Shioaji  
- **EventBus**：行情/委託/成交/風控/健康事件全事件流  
- **AuditRecorder**：落盤（raw + normalized + hash）  
- **ReplayRunner**：回放（同一日可完全重播）

### 2.2 事件與狀態機（核心）
- 下單不是函式呼叫；下單是「狀態機」：NEW_REQUESTED→ACKED→(PARTIAL)FILLED→… 或 REJECTED/UNKNOWN  
- 任何 replace/modify 視同新單，必重新跑：OrderGuard + DPB-aware + Risk gate

---

# ============ 機構級必補洞（全套一次補齊） ============

## 3) Spec Updater + Diff Stopper OS（TAIFEX 規格自動更新/差異警報）
### 3.1 目的
避免「交易所改規則 → 我們隔天開始狂退單/風控失真」。

### 3.2 設計（必做）
- `SpecSnapshot`（每日產生）：
  - product specs（TXF/MTX/TXO）  
  - DPB/OrderSizeLimits/SettlementRules（可摘要）  
- `SpecDiff`（與前一版 diff）：
  - tick size / multiplier / hours / limits / rule text hash  
- `DiffStopper`：
  - 若發現變更 → **預設進 SAFE MODE（禁止開新倉，只平倉）**  
  - 需要人工確認（或簽名）後才解除

### 3.3 驗收步驟（逐步）
1) 產生今日 spec snapshot（含 hash）  
2) 與昨日 diff  
3) 人為修改 snapshot → DiffStopper 觸發 SAFE MODE  
4) 解除 SAFE MODE 需在 audit 中留下 `SPEC_APPROVAL`

---

## 4) Reject Taxonomy OS（Reject/Error 字典 + Runbook 自動處置）
### 4.1 核心
**把拒單從“雜訊”變成“可治理訊號”。**

### 4.2 Reject 分類（最少）
- TAIFEX：DPB、price limit、size limit、session closed、invalid price/tick  
- Broker：permissions、risk check、rate limit、session invalid、account state  
- System：timeout、unknown state、payload mismatch、contract mismatch

### 4.3 自動處置表（Policy）
用 `reject_policy.yaml`（可版本化）定義：
- match 条件：{instrument, order_type, session, reject_reason_pattern}  
- action：cooldown、reprice ladder、switch order type、reduce aggressiveness、kill-switch  
- caps：每分鐘最多重試 N 次；連續 reject 超過 M 次直接停交易

### 4.4 驗收
1) 製造 size-limit reject → 觸發 OrderSlicer 修正後成功  
2) 製造 DPB reject → 觸發 DPB-aware reprice ladder，不進 reject storm  
3) 連續 N 次 reject → kill-switch + 報告輸出（原因分布、建議）

---

## 5) Reconciliation OS（三方對帳：委託/成交/部位/資金）
### 5.1 為什麼是終極門檻
實盤最致命的是「我以為」：  
以為沒成交/以為已平倉/以為部位為 0 → 其實不是 → 黑天鵝發生。

### 5.2 對帳引擎
- `OrderBookLocal`：本地委託狀態（由 OrderState events 驅動）  
- `FillsLocal`：本地成交記錄（由 Deal events 驅動）  
- `PositionsLocal`：本地部位（由 fills 聚合）  
- `BrokerTruth`：若 API 支援，定期拉：open orders / positions / margin/cash  
- `ReconcileLoop`：每 N 秒比較本地與券商真相：
  - 若不一致：進 SAFE MODE（reduce-only/flatten），並生成 `RECONCILE_ALERT`

### 5.3 驗收
1) 人為注入缺失 event → 引擎偵測不一致 → SAFE MODE  
2) 恢復一致後可解除（需 audit 紀錄）  
3) 每日產出 `RECONCILIATION_REPORT`

---

## 6) Latency/Backpressure OS（延遲預算 + 堆積治理）
### 6.1 延遲預算（Latency Budget）
必須明確定義並監控：
- market_data_lag_ms（最後一筆行情距離現在）  
- event_queue_depth（事件堆積）  
- decision_latency_ms（特徵→signal）  
- order_roundtrip_ms（送單→ACK）  
- fill_latency_ms（送單→成交）

### 6.2 Backpressure Governor
- queue depth 超過門檻：
  - 方案 A：drop policy（保留最新、丟棄舊 tick）或  
  - 方案 B：降級（停新倉，只平倉）  
- latency 超過門檻：  
  - 自動降 aggressiveness（改用更保守 order type / 更小 size / 更少頻率）  
  - 或直接停交易（視策略週期）

### 6.3 驗收
1) 模擬 tick 爆量 → queue depth 上升 → governor 生效  
2) 模擬延遲暴增 → 進入降級模式  
3) 恢復後自動回到正常（需 cooldown 防抖）

---

## 7) Cost Model OS（分場景交易成本模型）
### 7.1 必備成本項
- 明確費用：手續費、期交所費用/稅費（依商品與券商）  
- 隱含成本：spread、slippage、impact（隨波動/時段）  
- 退單成本：DPB/size-limit/retry 機會成本（用 proxy）

### 7.2 分場景
- 日盤 vs 夜盤（流動性差異）  
- 波動 regime（low/normal/high）  
- order type（market/limit/MWP）  
- size（切單筆數增加→成本上升）

### 7.3 Gate
- 研究/回測/實盤評估一律用「含成本」績效；未含成本一律視為無效。

---

## 8) Options Stress Battery OS（TXO 壓測電池 + Hedging 成本爆炸防線）
### 8.1 必跑情境（每週、每次策略更新都要跑）
- Underlying jump：±2σ、±4σ、gap jump  
- IV shock：±5%、±10%、skew twist、surface shift  
- 流動性惡化：spread x2/x3、impact x2  
- Hedging frequency：每 1、3、5、10 秒（離散避險成本曲線）

### 8.2 Gate（不過就禁上線）
- max loss under stress  
- margin_ratio worst-case  
- hedging cost 爆炸時 kill-switch 是否有效

---

## 9) Auto-Remediation OS（監控→自動處置）
### 9.1 監控不是通知，是自動行動
監控指標（例）：
- reject_rate、dpb_reject_rate、avg_roundtrip_ms、quote_stale_s、margin_ratio、position_delta  
自動處置（例）：
- quote stale > N 秒 → 禁止開新倉，只平倉  
- reject_rate > 阈值 → cooldown + 降 aggressiveness  
- margin_ratio > 阈值 → 進入 YELLOW/ORANGE/RED（Margin OS）  
- latency > 阈值 → backpressure governor 降級

### 9.2 驗收
1) 人為造成 quote stale → 系統自動停止開倉  
2) 人為造成 reject storm → 自動 cooldown/kill-switch  
3) 產出 `AUTO_REMEDIATION_REPORT`

---

## 10) Drill OS（演練文化：把黑天鵝變流程）
### 10.1 每月必跑 Drill（至少）
- Disconnect drill（行情斷線/重連/重新訂閱）  
- Reject storm drill（DPB/size-limit/price-limit）  
- Margin shock drill（保證金上調 + 跳空）  
- Night liquidity drill（夜盤 spread 擴大、成交率下降）  
- Options jump drill（TXO gamma/jump）

### 10.2 產物
- `DRILL_REPORT_YYYYMMDD.md`（通過/失敗、改善項、下次目標）  
- 每次 drill 都要能 replay（Audit+Replay 必須完整）

---

# ============ 額外加強（v16 追加的「工程生存力」） ============

## 11) Secrets/Config/版本治理 OS
- secrets 永不寫入 repo；分環境（SIM/PAPER/LIVE）  
- config 版本化（commit hash + sha256），每次交易日落盤當日 config snapshot  
- feature flag：新策略/新 execution policy 必須能一鍵關閉  
- 關鍵風控參數修改需 audit（可選雙簽）

## 12) CI/Release OS（研究→上線的關卡化）
- unit tests（OrderGuard/DPB policy/reconcile）  
- integration tests（Shioaji test report runner）  
- replay regression（固定樣本日 + 固定 events）  
- release artifact：zip + sha256 + changelog

## 13) Time Sync OS（時鐘一致性）
- 記錄：ts_exchange、ts_local、clock_offset_estimate  
- clock drift 超限 → SAFE MODE（避免延遲判斷失真）

## 14) Data Quality OS（資料品質門檻）
- tick/bidask 缺失率、時間倒序、異常跳價、重複事件  
- 不過門檻 → 禁止開新倉（只平倉）

## 15) Paper→Live 的上線門檻 OS
- Paper 連續 N 交易日：
  - 含成本 PF、worst-day、max drawdown、reject rate、fill rate、latency 皆達標  
- 再允許 live（且先小額/限口數）

---

## 16) v16 主線落地清單（我接下來寫程式必照做）
### 16.1 必做模組（新增/強化）
- `spec/spec_updater.py` + `spec/spec_diff_stopper.py`  
- `execution/reject_taxonomy.py` + `execution/reject_policy.yaml`  
- `ops/reconcile/reconcile_engine.py`  
- `ops/latency/latency_budget.py` + `ops/latency/backpressure_governor.py`  
- `research/cost_model/cost_model_os.py`  
- `risk/options/stress_battery.py`  
- `ops/auto_remediation/auto_remediation_engine.py`  
- `ops/drills/drill_runner.py`  
- `ops/audit/audit_recorder.py` + `ops/replay/replay_runner.py`（v15 延伸）

### 16.2 Acceptance Steps（逐步）
**A. Spec Updater**：snapshot→diff→stopper→approval 解鎖  
**B. Reject OS**：政策檔→分類/處置→storm→kill-switch  
**C. Reconcile OS**：一致→注入不一致→SAFE MODE→解除  
**D. Latency OS**：queue 壓力→governor→降級/恢復  
**E. Options Stress**：battery→gate（不過禁上線）  
**F. Drills**：disconnect/reject/margin/options→報告+replay

---

# 附錄：v15 原文（完整保留，供回溯）
# TMF AutoTrader 量化交易開發聖經（OFFICIAL-LOCKED v15 TAIFEX-HARD-CONSTRAINTS + SHIOAJI-AUDIT）
**日期**：2026-01-31（Asia/Taipei）  
**適用範圍**：TXF / MTX / TXO（research → paper → live）  
**券商執行**：永豐金（Sinopac）Shioaji  
**定位**：v15 = v14（Sinopac Broker OS）之上，新增「**TAIFEX 硬約束（會直接退單/失真/爆倉）**」的工程化落地：  
- **動態價格穩定措施（DPB/DPBM）退單邏輯** → 變成 execution 的硬處理  
- **order size limits（market/limit/MWP + regular/after-hours）** → 變成 OrderGuard 的切單器  
- **交易所接受的 order types** → 變成策略/執行層的可用集合  
- **結算價定義（daily settlement）** → 變成 mark-to-market 與日內風控的真相源  
並把這些規則全部納入 **Audit（稽核）**：每一次拒單/改價/切單/重試都要留下可回放證據。

> **唯一讀者：主線開發視窗的我（助理）。**  
> v15 的目的不是「更長」，而是把最容易踩雷的交易所/券商硬規則「寫死成程式必遵守的 OS」。

---

## 0) v15 新增最高硬規則（Non‑Negotiables）
1) **只要 TAIFEX 會退單，我們就必須在送單前先預防**：把 DPB + order size limits 寫入 `OrderGuard`，否則 live 會進入 reject storm。  
2) **改價（modify/replace）等同新單**：所有改價都要重新跑 DPB 檢核策略與切單策略。  
3) **成交真相源只認 events**：Shioaji 的 OrderState / Deal events 是唯一真相，禁止以「呼叫成功」當作委託成立。  
4) **Audit-first**：任何下單相關事件必落盤（含原始參數、切單後子單、回報、reject reason、重試序列、當時行情快照 hash）。

---

## 1) TAIFEX HARD CONSTRAINTS（必須工程化寫入程式）

### 1.1 動態價格穩定措施（DPB/DPBM）— 退單的「真實邏輯」
**TAIFEX 會針對每一筆「新進委託」試算可能成交價；若可能成交價超出即時價格區間上下限 → 退單。**  
- 買單：可能成交價 > 區間上限 → 退單  
- 賣單：可能成交價 < 區間下限 → 退單  
關鍵細節（務必寫入 OS）：
- **只檢核新進委託**；但「改價」會被當成新單重新檢核。  
- 衍生單（implied orders）不適用；但**選擇權組合式委託**會逐腿檢核，任一腿逾越則整筆退單。  
- 英文資料明確指出：TAIFEX 會用委託簿模擬撮合價格（simulated matched price）來判斷是否退單；也就是你即使掛的是 market / MWP / limit，都可能因試算成交價觸發退單。  

**工程化落地（必做）**
- `DPB_Aware_RepricePolicy`：送單前先做「保護價格」或「分段送單」，避免模擬成交價跨出區間。  
- `RejectClassifier`：凡是 DPB reject → 立即降級（cooldown + reduce aggressiveness + reprice ladder）。  
- `ModifyIsNewOrder`：任何 cancel/replace（改價）一律當新單，重新走 DPB 預防流程。

### 1.2 Order types（交易所接受的基本集合）
TAIFEX 接受 **market / limit / market with protection (MWP)** 作為基本可執行類型；其他更複雜型態可能由期貨商自行提供（如 stop/stop-limit/OCO 等）。  
**工程化落地（必做）**
- `AllowedOrderTypeRegistry`：對於 TAIFEX 層級，至少支援 market/limit/MWP；策略層僅能宣告「urgency」，由 execution 選擇合適 order type。  
- **禁止策略直接指定 stop/OCO**（除非我們在 execution 層已做完完整狀態機與退單處理，且券商端支援明確）。

### 1.3 Order size limits（最常見退單/拒單來源）
TAIFEX 公開 FAQ 與 Order Size Limits 頁面指出（摘要）：
- **Market order**：regular 最多 **10** 口；after-hours 最多 **5** 口（全類型期貨與選擇權）。  
- **Limit / MWP**：其他期貨（非單一股票）每筆最高 **100** 口；其他選擇權每筆最高 **200** 口（單一股票期貨/權另有更高上限）。  

**工程化落地（必做）**
- `OrderGuard.max_lot(order_type, session, instrument_kind)`：以交易時段 + order type + instrument 決定上限。  
- `OrderSlicer`：若 intent 超過上限，自動切成多筆子單（且每筆都必須走 DPB 預防流程）。  
- 任何「未切單就送」造成 reject → 視為 bug（不允許靠人修）。

### 1.4 結算價（daily settlement price）的真相源
TAIFEX 指出：日結算價通常用 regular session 最後 1 分鐘成交量加權平均價（VWAP）等方法決定（或依規則另定）。  
**工程化落地（必做）**
- `MarkToMarketEngine`：日內風控的「基準價」要能切換：last / mid / settlement_estimate（接近收盤時用）。  
- `EOD_RiskLock`：靠近 regular 收盤與最後交易日收盤，必須切換到更保守 profile（避免用錯基準導致風控延遲）。

---

## 2) Shioaji-AUDIT 強化（v15 針對證據可回放做硬化）

### 2.1 Order & Deal Event：唯一真相源（再強化）
Shioaji 文件說明：place/cancel/update 都會回傳 OrderState；若不想收回報，可在 login 時把 `subscribe_trade=False`。  
**v15 硬規則**
- Live 交易必須 `subscribe_trade=True`（預設），否則沒有回報就無法稽核/回放。  
- 所有 OrderState/Deal event 必須落盤（原始 payload + 正規化欄位）。

### 2.2 測試報告與下單測試間隔（合規 OS）
Shioaji 條款/測試頁面提到：股票與期貨需分開測試，且下單測試需間隔大於 1 秒等要求。  
**v15 硬規則**
- `BrokerPreflight` 必須包含：測試模式下的「節流器」(>=1s)；違規直接中止測試。  
- `TestArtifacts`：每次測試輸出：版本、環境、成功/失敗、回報截圖/摘要、reject reason。

---

## 3) v15 主線工程落地清單（我寫程式必照做）

### 3.1 新增/強化的必做模組
1) `execution/dpb_aware_policy.py`（DPB 預防：reprice ladder / slicing / cooldown）  
2) `execution/order_guard_taifex_limits.py`（market 10/5、limit/MWP 100/200 等切單規則）  
3) `risk/mark_to_market_engine.py`（settlement-aware mark）  
4) `ops/audit/audit_recorder.py`（下單全事件落盤 + 可回放 index）  
5) `ops/audit/reject_storm_report.py`（reject reason 分布 + DPB/size-limit 追蹤）

### 3.2 驗收步驟（逐步）/ Acceptance Steps（v15）
**A. TAIFEX Limits**
1) 以 unit test 驗證 market order 在 regular 切成 <=10、after-hours 切成 <=5  
2) 以 unit test 驗證 limit/MWP 在期貨 <=100、選擇權 <=200（非單一股票情境）  
3) 超限 intent 會自動 slicing，且每筆子單都有 audit 記錄

**B. DPB Prevention**
1) 模擬委託簿（或以保守 proxy）觸發「可能成交價越界」案例  
2) DPB-aware policy 能自動 reprice/cooldown，不會陷入 reject storm  
3) 改價（replace）會重新走 DPB 檢核（ModifyIsNewOrder）

**C. Audit & Replay**
1) 任一交易日可一鍵 replay：行情 → intent → 子單 → 回報 → 成交 → 風控事件  
2) 任一 reject 都能追溯：原 intent、切單、當時 session、order type、當時行情快照 hash  
3) 產出 `DAILY_AUDIT_REPORT_YYYY-MM-DD.md`

---

## 4) v15 對主線開發的直接影響（我必須記住）
- 策略研發再強，沒有 **DPB/size-limit/事件回報稽核**，live 一定會被拒單風暴與滑價打死。  
- 所以主線優先順序：  
  1) **OrderGuard（TAIFEX limits）**  
  2) **DPB-aware execution**  
  3) **Audit+Replay**  
  4) 才是更多策略

---

## 5) 權威來源（我遇到衝突時以此為準）
- TAIFEX：DPB 介紹、Order Types、Order Size Limits/FAQ、TXF 產品規格、settlement 說明  
- Shioaji：Order & Deal Event、streaming、terms/test requirements  

---

# 附錄：v14 原文（完整保留）
# TMF AutoTrader 量化交易開發聖經（OFFICIAL-LOCKED v14 SINOPAC-SHIOAJI BROKER OS）
**日期**：2026-01-31（Asia/Taipei）  
**適用範圍**：TXF / MTX / TXO 全自動量化交易系統（research → paper → live）  
**交易執行與券商**：**永豐金（Sinopac）API / Shioaji**（期貨與選擇權下單、行情串流）  
**定位**：v14 = v13（TAIFEX-SPEC + Margin OS + TXO-Hedging）之上，新增「**券商適配 OS（Broker OS）**」：把 Shioaji 的**登入/契約/行情串流/下單/回報/斷線重連/錯誤處理/測試報告與合規限制**寫成可落地的架構與驗收規範。  
> **唯一讀者：主線開發視窗的我（助理）。**我必須照此文件把系統做成可長期運行、可回放、可降級、可稽核的台指期/小台/台指選擇權全自動交易系統。

---

## 0) v14 的新增最高硬規則（Non‑Negotiables）
1) **Shioaji 不是函式庫，而是交易系統的一部分**：所有回調（quote/order/deal）都是「真實事件流」，必須進入事件總線（Event Bus）與可回放紀錄。  
2) **永豐金/ Shioaji 的限制與流程必須工程化**：包含測試報告規範、下單測試間隔、可測試時間、台灣 IP 限制（若存在）等；不把它變成自動化檢查＝上線一定踩雷。 citeturn0search21  
3) **下單=狀態機**：place/cancel/replace 的結果以 order event 為準，不得以「呼叫成功」假設委託存在。 citeturn0search0  
4) **行情斷線與重連是常態**：必須有重連策略與「重新訂閱」策略，並且可觀測（latency/丟包/queue backlog）。 citeturn0search1turn0search20  
5) **策略不得直接碰 Shioaji API**：策略只能吐出 OrderIntent；實際下單由 ExecutionEngine + BrokerAdapter 統一負責，避免 callback 亂入造成重複下單。

---

## 1) Shioaji Broker OS：總體架構（必須長這樣）

### 1.1 分層（Hard Separation）
- **StrategyEngine**：只做 signal/state，不下單  
- **RiskEngine**：所有 gating / sizing / kill-switch  
- **ExecutionEngine**：將 OrderIntent 轉換成「可執行的下單序列」（slicing/retry/reprice）  
- **BrokerAdapter（ShioajiAdapter）**：唯一能呼叫 Shioaji 的模組（login/subscribe/place/cancel）  
- **EventBus**：Tick/Book/OrderUpdate/Fill/Risk/Health 全部事件流化  
- **Recorder + Replay**：事件與配置落盤（可重播重現）

> Shioaji 官方文件把「下單事件（order event）」視為回報核心：place/cancel/update 都會回傳 order state。 citeturn0search0

---

## 2) Shioaji 連線生命週期（Login OS + Reconnect OS）

### 2.1 Login OS（必做）
- 啟動流程：
  1) 讀取 secrets（分環境：SIM / PAPER / LIVE）  
  2) `api.login(...)`  
  3) 拉取 contracts（或至少確保合約查詢可用） citeturn0search6  
  4) 啟動 quote 連線（streaming）並建立監控：latency、message rate、queue depth citeturn0search1  
  5) 註冊 callbacks（tick/bidask/order/deal），全部只做「轉事件」不做邏輯  
  6) 啟動 HealthCheck（每 N 秒）：連線狀態、心跳、延遲、最近一筆行情時間

### 2.2 Reconnect OS（必做）
- 斷線偵測：  
  - 超過 `N` 秒沒收到 tick/bidask  
  - quote session event 觸發  
- 重連策略：  
  - exponential backoff（含上限）  
  - 成功重連後「重新訂閱所有 topic」  
  - 使用 quote-binding queue 時，重連後要丟棄舊 queue、重建 queue（避免處理到不一致序列） citeturn0search20  
- 降級模式：  
  - 若行情不可用：禁止開新倉、只允許減倉/平倉  
  - 若下單回報不可用：停止交易（避免黑盒重複下單）

---

## 3) 行情串流（Market Data OS）

### 3.1 Streaming 的工程規格
Shioaji 提供 streaming market data 教學，並提及重連後可能遇到 publisher flow 等 session event。 citeturn0search1  
我必須把行情串流做成：
- **單向資料管線**：callback → decode/normalize → EventBus → FeatureStore  
- **Backpressure**：queue 長度超限時採取策略：
  - drop policy（只保留最新）或  
  - 降級（停止交易）  
- **時間戳規則**：事件必須帶 `ts_exchange` 與 `ts_local`，並記錄時鐘偏移

### 3.2 Quote‑Binding Mode（可選，但若用就要嚴格）
Shioaji 的 quote-binding mode 可把 tick/bidask 推入 queue、送 redis、或在 callback 內觸發 stop order。 citeturn0search20  
v14 規則：
- **禁止在 quote callback 內直接下單**（會造成不可控重入與延遲抖動）  
- quote-binding queue 只能做「轉發事件」與「指標快取」，下單必須走 ExecutionEngine 的單一入口

---

## 4) 下單與回報（Order/Deal OS）

### 4.1 Futures/Options 下單流程（核心文件點）
Shioaji 教學區有 Futures & Option 下單說明與期貨 order/deal event。 citeturn0search2turn0search0  
v14 強制規範：
- `place_order` 回傳不是最終真相；最終真相是 **order event / deal event**  
- 必須把 order state 機械化成以下狀態：
  - `NEW_REQUESTED`（我送出 intent）  
  - `ACKED`（系統回報委託成立/已送出）  
  - `PARTIAL_FILLED` / `FILLED`  
  - `CANCEL_REQUESTED` / `CANCELED`  
  - `REJECTED`（必須攜帶 reason，進入 reject-runbook）  
  - `UNKNOWN`（回報缺失/延遲過久，進入安全模式）

### 4.2 Idempotency（防重複下單）
- 每個 OrderIntent 必須生成 `client_order_id`（可重複重送但不會重下）  
- BrokerAdapter 必須做「去重表」（TTL）  
- 若回報缺失超時：  
  - 先查詢現有委託/部位（若 API 允許）  
  - 不確定就進入 **reduce-only** 模式直到人工確認

### 4.3 Rejected/Fail Runbook（必做）
- **Rejected 原因分類**（至少）：
  - 交易所限制（price limit / DPB / size limit）  
  - 券商限制（測試/權限/帳務）  
  - 參數錯誤（合約代碼、價格格式）  
  - 系統風險（rate limit / session invalid）  
- 每一類都要有處置策略：  
  - reprice & retry（有上限）  
  - cooldown（避免 storm）  
  - kill-switch（連續 N 次 reject）  
- 這些必須在 ExecutionEngine 的狀態機內自動完成

---

## 5) 合規與測試報告（Shioaji Terms / Test OS）
Shioaji 的服務條款/測試說明提到：  
- 測試報告只提供 Python（某些情境）  
- 可測試時間（週一至五 08:00~20:00）、部分時段可能限制台灣 IP  
- 證券/期貨需分別測試  
- 證券/期貨下單測試需間隔 ≥ 1 秒  
- 安裝版本注意事項（依版本而定） citeturn0search21  

v14 規則：把以上全部做成 **CI/Preflight**：
- `preflight_shioaji_env_check()`：
  - 檢查套件版本（鎖定可用版本範圍）  
  - 檢查時段（是否在允許測試時段）  
  - 檢查 IP/地理限制（若遇到失敗要明確提示）  
- `api_test_report_runner.py`：
  - 自動完成 login / place_order（遵守 1 秒間隔）  
  - 自動收集回報並輸出測試報告 artifacts

---

## 6) Shioaji 合約/商品查詢（Contract OS）
Shioaji 的 contract 文件指出合約可從 `api.Contracts` 取得，涵蓋 stocks/futures/options/indices。 citeturn0search6  
v14 規則：
- 啟動時 반드시做 `contract_snapshot`：
  - 把 TXF/MTX/TXO 的可交易合約、到期、履約價帶（TXO）做快照落盤  
- `ContractSpecRegistry`（v13）與 `ContractSnapshot`（Shioaji 實際合約）必須做一致性檢查：
  - tick size / multiplier / expiry calendar 差異 → 直接 fail-fast（避免用錯合約）

---

## 7) 速率限制與節流（Rate Limit OS）
雖然公開文件未必把所有 rate limit 數字寫死，但工程上必須假設：
- 行情 callback 高頻  
- 下單/改單/刪單若過快會觸發限制或系統風險

v14 硬規則：
- 下單頻率必須由 ExecutionEngine 統一節流：
  - per-instrument / per-account / global QPS 上限  
  - burst cap + cooldown  
- 並且在 `Observer` 中監控：
  - order QPS、reject rate、平均 round-trip latency

---

## 8) 主線工程落地清單（我接下來寫程式必照做）

### 8.1 新增必做模組
1) `broker/shioaji_adapter.py`（唯一 Shioaji 入口）  
2) `broker/shioaji_callbacks.py`（只負責事件轉發，不做邏輯）  
3) `broker/shioaji_preflight.py`（測試報告/時段/IP/版本檢查）  
4) `ops/run_shioaji_api_test_report.py`（自動測試報告產生器）  
5) `ops/run_shioaji_stream_healthcheck.py`（行情串流健康檢查）  
6) `schemas/broker_events.py`（OrderUpdate/Fill/Reject schema）

### 8.2 驗收步驟（逐步）/ Acceptance Steps（v14）
**A. Login/Reconnect**
1) 模擬/實盤帳號可 login  
2) streaming 能訂閱並收到 tick/bidask  
3) 手動斷線→自動重連→自動重新訂閱  
4) 重連後延遲與丟包在門檻內（超限進入降級）

**B. Order/Deal Events**
1) place_order 後能收到 order event（ACK/REJECT）  
2) 成交能收到 deal/fill event  
3) cancel/replace 能收到正確狀態流  
4) 超時/缺回報→進入 reduce-only 並寫 audit

**C. Reject Runbook**
1) 人為製造 size limit / price limit 類 reject  
2) 系統能分類、cooldown、必要時 kill-switch  
3) 產出 `REJECT_REPORT`（原因分布 + 建議處置）

**D. Test OS**
1) 自動跑測試報告（遵守 ≥1s 間隔）  
2) 時段/IP 限制時能給明確訊息  
3) 產出可交付 artifacts（log + summary）

---

# 附錄：v13 原文（完整保留）
# TMF AutoTrader 量化交易開發聖經（OFFICIAL-LOCKED v13 TAIFEX-SPEC + MARGIN-OS + TXO-HEDGING）
**日期**：2026-01-31（Asia/Taipei）  
**適用範圍**：TXF / MTX / TXO 全自動量化交易系統（research → paper → live）  
**定位**：v13 = v12（Full-Stack+Leverage+Hedging）之上，再把「會在真實市場直接打爆系統」的落地細節硬化成**規格表 + 狀態機 + 驗收清單**：  
- **TAIFEX 產品規格/交易時段/下單限制** → 直接變成 Execution/Risk 的硬規則  
- **保證金/槓桿/追繳風險（Margin OS）** → 變成日內總控與事故演練  
- **選擇權動態避險（Dynamic Hedging OS）** → 變成 Greeks+跳躍風險+離散避險成本模型  
- **期貨期限結構/跨期/換月（Futures Carry/Roll OS）** → 變成可測試的研究模組與上線限制

> **唯一讀者：主線開發視窗的我（助理）。**  
> 我必須能 100%照此文件做系統設計與實作；任何模組若不符合 v13，視為不合規，禁止合併主線。

---

## 0) v13 最高硬規則（Non-Negotiables）
1) **交易所規格是「系統約束」不是備註**：交易時段、最小跳動、契約乘數、下單口數上限、DPB/Price Limits、最後交易日/結算日規則 → 必須進入程式的 Schema、校驗器、狀態機。  
2) **Margin OS 優先於策略**：系統必須能在保證金壓力下自動縮倉/停機/只平倉，並有演練流程。  
3) **TXO 上線只允許「先風控後策略」**：先有 Greeks/Stress/Hedging cost model，才允許任何選擇權 alpha。  
4) **所有績效以「含成本/含滑價/含拒單&成交率」為準；否則一律無效。**

---

## 1) TAIFEX 產品規格（我在程式中必須硬編碼的「交易真實約束」）

> **注意**：規格以 TAIFEX 官方頁面為準；任何變動都要更新到 `ContractSpecRegistry`，並觸發 regression。  
> 這一節要落地成：`contracts/specs.py`（或同等模組）+ 單元測試 + runtime 校驗器。

### 1.1 TXF（台指期）官方摘要（英文頁）
- **Regular session**：08:45–13:45；最後交易日 08:45–13:30  
- **After-hours**：15:00–翌日 05:00；最後交易日無夜盤  
- **Contract size**：NTD 200 × 指數點  
- **Min tick**：1 點（NTD 200）  
- **Price limits**：±10%（以前一日結算價為基準）  
→ 以上內容要進 `TXF.spec`（且提供 session 判斷函式）。  

### 1.2 MTX（小台）官方摘要
- 同 TXF 時段  
- **Contract size**：NTD 50 × 指數點  
- **Min tick**：1 點（NTD 50）  
- **Price limits**：±10%  
→ 以上內容要進 `MTX.spec`。  

### 1.3 TXO（台指選擇權）官方摘要
- 同 TXF 時段（regular/after-hours/最後交易日）  
- **Contract size**：常見為 NTD 50 × 指數點（請以 TAIFEX TXO 規格頁為準）  
→ 以上內容要進 `TXO.spec`，並擴充 `OptionSpec`（行權價距、tick size for premium、週選/月選代碼等）。  

### 1.4 下單口數限制（必須進 OrderGuard）
TAIFEX FAQ 指出：  
- Market order 口數限制更嚴格（regular 10、after-hours 5 之類限制）  
- 非市場單（限價/保護市價）有更高上限（例如期貨 100 口等級）  
→ 這必須在 `OrderGuard.validate()` 裡做：依 session + order_type + instrument 自動拒絕或切單。  

### 1.5 SPAN / 保證金參數（必須進 Margin Engine）
TAIFEX SPAN 參數頁提供 index options 與其他商品的風險參數倍數表。  
→ 這要做成 `MarginParamProvider`：每日抓取/更新（或手動更新，但必須可稽核）。  

---

## 2) ContractSpecRegistry（必做模組）
**目的**：避免「策略寫得很漂亮，上線被交易所規格打死」。  

### 2.1 必備欄位（最少）
- `symbol` / `product`（TXF/MTX/TXO）  
- `multiplier`、`tick_size`、`tick_value`  
- `sessions`（regular/after-hours + last_trading_day overrides）  
- `price_limit_rule`（±%）  
- `order_size_limits`（by order_type, session）  
- `expiry_rule`（monthly/weekly, third Wednesday 等）  
- `is_last_trading_day(ts)`、`is_after_hours(ts)`、`trading_session(ts)`  

### 2.2 驗收（逐步）
1) 用 TAIFEX 官網資料建立 spec  
2) 單元測試：常見時間點（週一、最後交易日、夜盤跨日）  
3) runtime 啟動時：載入並校驗（缺欄位直接 fail-fast）

---

## 3) Margin OS（保證金/槓桿/追繳）— v13 升級硬化

> v12 已有「槓桿與分數 Kelly」；v13 要把它落到「保證金狀態機」與「事故演練」。

### 3.1 Margin Engine 必備能力
- 即時計算：`available_margin`, `used_margin`, `margin_ratio`  
- 壓力測試：在 **gap jump / vol spike / margin up** 下的 margin_ratio  
- 對 TXO：要計入 Greeks stress 與 SPAN 參數（至少近似模型）

### 3.2 Margin Kill-Switch 狀態機（必做）
- **GREEN**：正常  
- **YELLOW**：margin_ratio 達到警戒（例如 70%）→ 禁止加倉、只能減倉  
- **ORANGE**：更高警戒（例如 85%）→ 強制縮倉到 target exposure，並限制下單頻率  
- **RED**：危險（例如 95%）→ **只允許平倉**、立刻停止所有策略、通知  
- **BLACK**：券商/交易所異常或 margin 不可得 → 直接 flatten（或進入手動接管模式）

### 3.3 Margin 事故演練（每月必跑）
- 模擬保證金上調 + 跳空 + 夜盤低流動性  
- 驗收：Kill-switch 能否在 1 秒內停止加倉並啟動縮倉/平倉  
- 產物：`DRILL_REPORT_MARGIN_YYYYMMDD.md`

---

## 4) TXO Dynamic Hedging OS（把 Dynamic Hedging 變成工程規格）

> Dynamic Hedging 的核心不是「會算 Greeks」而已：  
> **離散避險 + 跳躍 + 微結構成本** 會把理論 PnL 變成真實虧損。

### 4.1 TXO 上線前必備的三個模型
1) **Greeks Engine**（Δ/Γ/ν/θ）  
2) **Discrete Hedging Cost Model**：以 hedge frequency、spread、impact 估算成本  
3) **Jump/Gap Stress Model**：±2σ/±4σ + gap jump + IV shock + skew twist

### 4.2 Greeks Risk Guard（必做）
- `net_delta_limit`（避免方向曝險超過策略預期）  
- `net_gamma_limit`（避免跳價造成爆炸）  
- `net_vega_limit`（避免 vol regime 轉換毀滅）  
- `theta_budget`（避免長期 θ burn 吃掉 edge）  
觸發即進入 **hedge-only / reduce-only / flatten** 狀態。

### 4.3 Hedging Policy（必做）
- `hedge_mode`：none / periodic / event-driven（價格跳動超過閾值）  
- `hedge_instrument`：TXF/MTX（線性對沖）或選擇權腿（非線性對沖）  
- `hedge_frequency_cap`：避免因噪音過度交易  
- 必須同時看：fill rate、slippage、hedge cost，否則 hedging 會「越避越虧」。

---

## 5) Futures Carry/Roll OS（期貨期限結構/跨期/換月）
> 目標：把「跨期/換月」做成可回測、可落地、可風控的模組，避免價格跳空污染策略。

### 5.1 研究模組（Research-only → Paper → Live）
- `continuous_contract_builder`：back-adjusted / ratio-adjusted / none  
- `calendar_spread_engine`：近月-遠月價差、roll yield proxy  
- `roll_calendar`：最後交易日前 N 天（可配置）進入 roll mode  
- `roll_mode`：禁止新增方向部位、只允許減倉/移倉、或只做價差腿

### 5.2 Live 硬規則
- 進入 roll window：  
  - 禁止新增「非對沖」方向性倉位  
  - 允許的動作只有：平倉、移倉、價差腿（若策略屬於 spread family）

---

## 6) Strategy Factory v13：把「可執行性」與「生存性」變成第一級目標
v10/v11/v12 的 Gate A/B/C 保留；v13 新增：
- **Gate B2（Exchange Constraints）**：  
  - DPB/price limit 觸發頻率  
  - reject reason 分布  
  - order size limit 切單成功率  
- **Gate C2（Margin Survival）**：  
  - margin_ratio worst-case（99%）  
  - margin shock survival（保證金上調）  
- **Gate C3（Options Jump Survival）**：  
  - gamma stress 下的 max loss  
  - hedging cost 爆炸時的 kill-switch 行為

---

## 7) 工程落地清單（我接下來寫程式必照做）

### 7.1 必做檔案/模組（命名可調，但職責不可少）
1) `contracts/spec_registry.py`（TAIFEX specs + session rules + order limits）  
2) `risk/margin_engine.py`（margin calc + margin states）  
3) `risk/options_risk_engine.py`（Greeks + stress + hedging policy guard）  
4) `execution/order_guard.py`（order size limits + DPB-aware reprice/retry）  
5) `research/roll_engine.py`（continuous contract + roll calendar）  
6) `ops/drills/`（margin drill + disconnect drill + reject storm drill）

### 7.2 驗收步驟（逐步）/ Acceptance Steps（v13）
**A. Contract Specs**
1) 建 spec（TXF/MTX/TXO）  
2) 測試 session/最後交易日  
3) 測試 order size limits（market vs limit）  
4) 啟動時校驗（缺即 fail）

**B. Margin OS**
1) margin_ratio 即時計算 OK  
2) YELLOW/ORANGE/RED/BLACK 狀態切換測試  
3) RED 只能平倉（加倉會被拒）  
4) 產出 drill report

**C. TXO Hedging OS**
1) Greeks 計算可用（或近似版）  
2) stress 報告可產出  
3) 觸發 gamma/vega limit → hedge-only/reduce-only 生效  
4) hedging cost 模擬+上限生效

**D. Roll OS**
1) continuous contract builder 跑通  
2) roll window 模式切換測試  
3) roll 模式下方向單禁止（除非對沖/價差）

---

# 附錄：v12 原文（完整保留）
# TMF AutoTrader 量化交易開發聖經（OFFICIAL-LOCKED v12 FULL-STACK + LEVERAGE + HEDGING）
**日期**：2026-01-31（Asia/Taipei）  
**適用範圍**：TXF / MTX / TXO 全自動量化交易系統（research → paper → live）  
**定位**：v12 = 以 v11 為底，額外整合 **Systematic/Smart Portfolios（組合與風險目標）**、**Fortune’s Formula（Kelly/下注理論）**、**Leveraged Trading（槓桿/保證金/爆倉風險）**、**Dynamic Hedging（選擇權與離散避險/跳躍風險）**、**Advanced Futures Trading Strategies（期貨期限結構/跨期/roll）**，並把它們「翻譯成可直接落地成模組、接口、守門機制、驗收清單」的工程規範。

> **讀者只有一個：後續主線開發視窗的我（助理）。**  
> 這份文件的成功定義是：我照著做，就能把系統做成「長期大賺小賠、穩定、可擴充、可回放、可降級、可治理」的台指期/小台指/台指選擇權全自動交易系統。  
> （誠實聲明：我已針對每本書的關鍵章節做抽取式閱讀與交叉整合，而非逐頁逐行背誦；但已足以形成可實作的工程化規範。）

---

## 0. v12 的「不可違抗硬規則」（Non-Negotiables）

### 0.1 任何策略要上線，必須同時通過三重硬門（Gate A/B/C）
- **Gate A：統計有效性**（反 data-snooping / overfit / regime 誤判）
- **Gate B：可執行性**（微結構/滑價/成交率/拒單/交易所機制）
- **Gate C：可生存性**（槓桿/保證金/尾部風險/跳躍風險/斷線風險）

> **一律以「含成本 + 含滑價 + 含拒單/成交率」的 OOS 結果為準。**
> 只要有一個 Gate 不過，策略視為「研究玩具」，禁止進入 paper/live。

### 0.2 風控地位高於 Alpha（Risk > Alpha）
- Alpha 可以換、可以死；  
- **風控、可追溯、可回放、可降級、可止血** 永遠不可破。

### 0.3 槓桿與 Kelly：只允許「保守分數 Kelly + 多重封頂」
- **禁止全 Kelly、禁止高槓桿追報酬**；估計誤差會把你推向破產邊緣。
- Position sizing 的上限以三層封頂決定：  
  1) **風險預算（risk budget）**（每日/每週/每月最大損失）  
  2) **保證金/可用資金**（含追繳 buffer）  
  3) **滑價敏感度/流動性容量（capacity）**（越大越滑）  

---

## 1. 市場與產品：台指期 / 小台指 / 台指選擇權「工程視角」

### 1.1 交易所機制必讀（會直接造成拒單/爆倉/模型失效）
- **動態價格穩定措施（Dynamic Price Banding, DPB/DPBM）**：可能導致下單被拒、假突破、成交率下降，必須在 execution layer 中硬處理。  
- **夜盤流動性**：點差擴大、撮合變慢、跳價機率上升 → 需要單獨的風控參數集（Night Regime Profile）。  
- **結算/轉倉**：期貨與選擇權的到期/結算與保證金需求會改變策略的風險結構。

### 1.2 產品風險的核心差異（我在設計模組時必須記住）
- **期貨（TXF/MTX）**：線性曝險，主要風險 = 趨勢反向/跳空/槓桿/流動性。  
- **選擇權（TXO）**：非線性曝險，主要風險 = **Gamma/跳躍風險/波動率錯配/離散避險成本**。

---

## 2. 數據與特徵工程：從「K線迷思」走向「事件驅動 + 微結構 + 波動」

### 2.1 資料層分級（Data Tiers）
- **Tier-0（撮合/成交）**：tick trades、成交量、成交價  
- **Tier-1（五檔/委託簿）**：bid/ask depth、掛單變化、微價格（microprice）  
- **Tier-2（衍生指標）**：order flow imbalance、spread、realized vol、jump proxy  
- **Tier-3（期權/波動）**：IV surface、Greeks（Δ/Γ/ν/θ）、skew、term structure  

> 期貨策略可以只用到 Tier-0/2，但只要碰到短週期或夜盤，Tier-1 會大幅提升執行與風控準確度。  
> 選擇權策略 **必須有 Tier-3**。

### 2.2 Bar 的選擇：固定時間只是 baseline
- 固定時間 bar（1m/5m）只當作基準。
- 進階：volume bars / dollar bars / volatility bars / event bars（避免低流動期把噪音當訊號）。

### 2.3 特徵工程的「禁止事項」
- **禁止使用未來資訊**（含 close-to-close 的 lookahead、同 bar 內先後順序錯置）
- **禁止在研究階段就做「全資料最佳化」**（先把 OOS 撕裂，再談改進）

---

## 3. 研究方法論：把「賺錢的錯覺」打掉

### 3.1 假設 → 測試 → 失敗也要留下證據
每個策略研究都要有：
- Hypothesis（為什麼這個市場會有這個 edge）
- Failure mode（我預期它在哪些 regime 會死）
- Test plan（purged CV / walk-forward / embargo）
- Slippage & cost model（先定義，再測）

### 3.2 反 overfit 工具箱（我必須落地成 code）
- **Walk-forward + rolling window**：每一段都有 out-of-sample  
- **參數穩健性**：收益不能集中在「單點神參數」  
- **多重假設修正**：大量嘗試就必須做 reality check（不然等同 p-hacking）  
- **蒙地卡羅/重抽樣**：檢驗 path dependence 與尾部風險

---

## 4. 策略模組庫：我應該怎麼「工程化」策略（Signals ≠ Strategy）

策略 = **Signal + Execution Policy + Risk Policy + Monitoring Policy**

### 4.1 期貨 Alpha（TXF/MTX）
- 趨勢/動能：breakout、volatility breakout、time-of-day momentum  
- 均值回歸：range reversion、liquidity vacuum mean reversion（需微結構驗證）  
- 結構性：期限結構/跨期（calendar spread）、roll yield、開收盤結構、夜盤特性  

### 4.2 選擇權 Alpha（TXO）
- 波動率風險溢酬：short vol（必須有嚴格 tail risk 規則）  
- skew/term structure：calendar、diagonal、risk reversal  
- 波動率突破：long gamma（但要控 θ burn）

> **Dynamic Hedging 的核心提醒：**  
> 你不是在交易「方向」，你是在交易「二階風險」。Gamma 在跳躍/離散避險下會變成成本黑洞；  
> 所以所有 TXO 策略都要帶「離散避險成本模型」與「jump stress」。

---

## 5. Execution Layer：DMA/HFT 的思想，落到台指期的現實

### 5.1 Execution 是策略的一部分
- 同一個 signal，換不同的 execution（market vs limit vs sliced）結果可能完全相反。
- Execution layer 必須輸出可量化指標：  
  - fill rate、avg slippage、reject rate、latency、queue position proxy（若有五檔）

### 5.2 台指期的實作建議（可落地）
- 訂單策略（以「降低拒單/降低滑價」為主）：
  - **Passive-first**：先掛限價（或 market with protection），失敗再 aggress  
  - **Slicing**：把大單切小單，避免 impact  
  - **Time guards**：特定時段禁止追價（開盤、結算前、重大公告時段）
- DPB/拒單處理：
  - 任何 reject → 進入「cooldown + reprice + max retry」狀態機  
  - 若連續 reject 超過 N → 觸發 kill-switch（避免追價自殺）

---

## 6. Risk Layer：v12 的重點升級（Kelly + 槓桿 + 選擇權避險）

### 6.1 風控三層（Pre / Intra / Post）
- **Pre-trade**：單筆最大損失、最大槓桿、保證金 buffer、當日剩餘風險預算  
- **Intra-trade**：移動停損、波動率擴張降槓桿、異常跳價/流動性枯竭退出  
- **Post-trade**：連續虧損熔斷、日內 max drawdown、異常成交率/滑價觸發降級

### 6.2 槓桿：禁止用「帳面勝率」換「破產機率」
- 必須對每個策略計算：
  - 最大回撤分布、最差日分布、tail loss（99%/99.5%）  
  - margin shock scenario（保證金上調、跳空、流動性枯竭）

### 6.3 Kelly（Fortune’s Formula）的工程落地（保守版）
- 用 Kelly 思想來「決定風險曝險的上限」，但實作必須：
  1) 用 robust estimate（避免被少量樣本騙）  
  2) 用 **fractional Kelly**（例如 0.1～0.25 Kelly）  
  3) 再套上「日內/週內最大損失封頂」  
  4) 再套上「交易容量（滑價敏感度）封頂」

### 6.4 選擇權風控：Greeks + Jump + 離散避險成本
- 每個 TXO 策略必須輸出：  
  - net Δ / net Γ / net ν（vega） / θ burn  
  - stress：±2σ、±4σ、gap jump、IV shock、skew twist  
- 強制規則：  
  - Γ/ν 超過上限 → 立即降曝險或對沖  
  - 連續跳價造成 hedging cost 飆升 → 停止新增倉位

---

## 7. 組合與資金配置：從「單策略神話」到「多策略穩定」

### 7.1 核心目標：穩定性優先（risk-targeting）
- 每個策略輸出「forecast strength」與「risk estimate（σ/ES）」  
- 組合層做：
  - volatility targeting（把報酬波動壓穩）  
  - diversification（降低策略相關性）  
  - regime-aware weighting（夜盤/日盤、波動期/盤整期）

### 7.2 Smart Portfolios / Systematic Trading 的工程翻譯
- 把策略視為「alpha stream」，用一致規則做：
  - 風險標準化（同風險貢獻，不同槓桿）  
  - 相關性懲罰（避免同一類 edge 過度集中）  
  - 風險預算分配（risk parity / capped risk）

---

## 8. 系統工程：模組、接口、事件流（我寫程式必須長這樣）

### 8.1 最小可行的模組分層（必須）
1) **MarketData**：tick/bidask/options chain ingest  
2) **FeatureStore**：即時計算特徵（可回放）  
3) **StrategyEngine**：只做 signal + state（不下單）  
4) **PortfolioAllocator**：多策略加權、風險標準化  
5) **RiskEngine**：所有 gating / kill-switch / sizing  
6) **ExecutionEngine**：order state machine、重試、切單  
7) **BrokerAdapter**：Shioaji（或其他）下單/回報  
8) **Observer**：監控、告警、日報、回放

### 8.2 事件與資料模型（Event Schema）
- TickEvent / BookEvent / BarEvent / SignalEvent / OrderIntent / OrderUpdate / FillEvent / RiskEvent / HealthEvent  
- 每個 event 都必須帶：
  - ts_exchange, ts_local, source, instrument, session, seq_id, checksum(optional)

---

## 9. 自動化與治理：讓系統能「長期活著」

### 9.1 必須自動化的東西（不做就不准上線）
- 一鍵重放（replay）任意一天（含下單/回報的模擬）  
- 每日報告（含成本、滑價、拒單、風險事件、PnL attribution）  
- 監控告警（斷線、延遲、成交率下降、連續拒單、DPB 觸發）  
- 版本化配置（策略參數、風控閾值、交易時段 profile）

### 9.2 事故處理 Runbook（最常見死法）
- quote 斷線 / 延遲飆升  
- 下單回報卡住 / rejected  
- 夜盤流動性崩壞（spread 爆、跳價）  
- 保證金不足 / 追繳風險  
- 策略失控（連續追單、連續加碼）

---

## 10. 驗收步驟（逐步）/ Acceptance Steps（v12 全套）

> 這一節是給我自己在主線開發視窗「逐項驗收」用。  
> 每做完一個模組，就必須走完對應步驟，未通過不得合併到主線。

### 10.1 Research Gate（Gate A）
1) 建立研究實驗 ID（含資料期間、參數範圍、成本模型版本）  
2) 跑 walk-forward（train/val/test）  
3) 輸出：OOS 分段績效、穩健性圖、MC 重抽樣、reality check  
4) 只要 OOS 不穩 → 回到假設層修正（禁止用參數硬救）

### 10.2 Execution Gate（Gate B）
1) 以 tick/bidask 回放 signal → 模擬下單 state machine  
2) 指標：fill rate、avg slippage、reject rate、latency  
3) 壓力測試：開盤/結算/高波動/夜盤  
4) 任何 reject/滑價失控 → 必須先修 execution 或降級交易模式

### 10.3 Survival Gate（Gate C）
1) 壓力情境：gap jump、IV shock、DPB 連續拒單、保證金上調  
2) 檢查：max day loss、max drawdown、risk of ruin proxy  
3) Kill-switch：必須可觸發且能停止所有新單，並通知

---

## 11. 參考資源清單（我之後遇到問題要先查的地方）
- **交易所規則**：TAIFEX trading safeguard / dynamic price banding / QA  
- **執行/微結構**：Trading and Exchanges、Algorithmic Trading and DMA、High-Frequency Trading  
- **驗證/最佳化**：The Evaluation and Optimization of Trading Strategies、Evidence-Based Technical Analysis  
- **波動率/期權**：Volatility Trading、Dynamic Hedging  
- **槓桿/下注理論**：Fortune’s Formula、Leveraged Trading  
- **組合/資金配置**：Systematic Trading、Smart Portfolios、Machine Learning for Asset Managers  
- **台灣在地**：FinLab、Shioaji docs、QuantConnect Strategy Library（對照實作方式）

---

## 12. v12 → 下一步（給我自己的路線圖）
1) 先把 **Event Schema + Replay framework** 定死（所有模組才能一致）  
2) 做 **RiskEngine v1（pre/intra/post + kill-switch）**  
3) 做 **ExecutionEngine v1（DPB/reject state machine + slicing）**  
4) 做 **TXF/MTX baseline 策略庫**（最小可行：trend + mean reversion 各一）  
5) 再擴 **TXO volatility/hedging**（必須先有 Greeks + stress + hedging cost model）

---

# 附錄：v11 原文（保留以供追溯）
# TMF AutoTrader 量化交易開發聖經（OFFICIAL-LOCKED v11 MICROSTRUCTURE+EXECUTION+EVAL）
**日期**：2026-01-31（Asia/Taipei）  
**適用範圍**：TXF / MTX / TXO 全自動量化交易系統（research → paper → live）  
**定位**：v11 = 在 v10（ML-RIGOR+TXF-EDGE）之上，加入 **市場微結構/執行（DMA/HFT/Trading&Exchanges）**、**策略評估與最佳化（EOTS）**、**統計驗證的技術分析（EBTA）**、**波動率/選擇權交易（Volatility Trading）** 的可落地規範。  
**這份文件的唯一目的**：讓後續所有主線開發視窗的我（助理）**能直接照做、直接落地成程式碼與自動化流程**，並且在長期 OOS（Out-of-sample）保持「大賺小賠、穩定獲利」。

---

## 0. v11 相對 v10 的「新增硬規則」（我必須遵守）
1. **所有策略/風控的研發與上線，必須同時通過：**
   - (A) **統計有效性**（避免 data snooping / selection bias / overfit）
   - (B) **交易可執行性**（微結構、滑價、成交率、交易所機制、夜盤流動性）
   - (C) **風險可控性**（尾部風險、保證金、結算日、斷線/拒單）
2. **任何回測/模擬的績效指標，若未納入「交易成本 + 滑價 + 交易所規則限制」→ 一律視為無效。**
3. **策略不是「訊號」而已；策略 = 訊號 + 執行演算法 + 風控 + 監控 + 失敗處理。**  
4. **量化系統的第一性原理**：  
   - Alpha 可能變、規則會變、流動性會變；  
   - 但「風控、可追溯、可回放、可降級」必須永遠不變。

---

## 1. 終極目標與成功定義（Success Metrics）
- **全自動台指期/小台指/台指選擇權交易系統**，可長期運行，面對市場 regime 變化仍能自我約束、持續進化。
- 成功以「扣成本、含滑價」為準，並以 **rolling walk-forward** 評估：最大回撤、最差日損失、交易品質（成交率/滑價/拒單率）、穩定性（最差週/月可控）。

---

## 2. 研發總則：反回測作弊（AFML + EOTS + EBTA）
- **時間序列切分**：不可亂打散；避免 leakage  
- **Purged / Embargo**（AFML）：避免 label overlap  
- **Walk-forward**：訓練/驗證/測試三層滾動  
- **Reality Check / Bootstrap**：對抗 data mining bias  
- **成本敏感度曲線**：cost multiplier 1x→2–5x 仍需存活；不然 live 必死

---

## 3. 市場微結構（Trading & Exchanges / HFT）→ 直接落地的交易規則
- 必須顯式建模：spread、impact、depth、adverse selection、queue/cancel  
- TXF/MTX：日盤/夜盤流動性差異；開盤/收盤/結算日；拒單（例：動態價格穩定機制）  
- 策略與下單型態匹配：Momentum 偏 aggressive；MR/做市偏 passive + adverse selection 防護

---

## 4. 執行層（Algorithmic Trading & DMA）→ Execution Engine
### 4.1 統一介面（策略只能用這些呼叫）
- `target_position(symbol, qty, urgency, price_protection, time_limit)`
- `target_vwap(symbol, qty, horizon_sec, max_participation)`
- `cancel_all(symbol)` / `flatten_all(reason)`

### 4.2 內建演算法（至少）
- TWAP / VWAP(POV) / Implementation Shortfall 思路 / Iceberg Slice  
- 回報指標：fill_rate、avg_slippage、rejection_rate、queue_time、impact_proxy

### 4.3 Watchdog + 降級
- Quote 中斷、Rejected、延遲飆升 → 自動降 aggressiveness / 只平倉 / kill-switch

---

## 5. 波動率與選擇權（Volatility Trading）→ TXO edge
- RV/IV/曲面追蹤；Vol Regime Detector  
- 分階段上線：先用 vol 只調整期貨槓桿/風控 → 再做簡化 Greeks 監控 → 最後才做選擇權策略

---

## 6. Smart Portfolios：多策略組合（避免單策略崩壞）
- 多風格（Trend/MR/Vol/Orderflow）  
- Risk Parity / Vol Targeting / Drawdown-aware allocation  
- 風險預算程式化：每策略日虧/連虧/曝險上限、組合層回撤上限

---

## 7. 風控層（Risk Layer）— v11 硬規則
- per-trade max loss、daily loss limit、連續虧損停機、最大曝險/保證金使用率、結算日模式  
- 觸發 hard stop → 停新單、平/鎖倉、通知、寫 audit log

---

## 8. 工程化：可觀測、可回放、可回滾
- 觀測：Quote/Order latency、Fill rate、Reject reason distribution、PnL attribution、Regime label  
- 回放：任何 live 異常必須可用資料+參數重播還原

---

## 9. 外部權威資源（新增書單已納入 v11）
- Trading and Exchanges（微結構）  
- Algorithmic Trading and DMA（執行）  
- High-Frequency Trading（LOB/延遲）  
- The Evaluation and Optimization of Trading Strategies（穩健性/最佳化）  
- Evidence-Based Technical Analysis（統計驗證 TA）  
- Volatility Trading（波動率/hedging/資金管理）  
- **Dynamic Hedging：尚未收到 PDF，待補齊**

---

## 10. v11 主線推進順序（我接下來寫程式就照這個）
1) Risk Layer 狀態機 + audit log  
2) Execution Engine（TWAP/VWAP/IS）+ 拒單/斷線處理  
3) Market Data Pipeline（tick + bidask depth）+ latency 量測  
4) Research Harness（walk-forward + bootstrap + cost sensitivity）  
5) 策略 plug-in 化（可回放、可自動評估）  
6) 組合層（risk budget + vol targeting）

---

## 11. 待你補的資料
- 《Dynamic Hedging》PDF（目前未納入）


---

# v10 BASELINE（完整保留，供回溯與細節查閱）
> 說明：以下為 v10 主要內容原文保留；若與 v11 衝突，以 v11 為準。

## 0) v10 的不可妥協原則（我必須遵守）

### 0.1 研究原則（避免假策略 / 回測作弊）
1) **Theory-first**：先提出「可反駁的理論」，再做策略規則與回測；沒有理論支撐的規則很可能是「假策略」。  
2) **Label / CV / Leak 三件套**：  
   - Label 必須對齊交易目標（期望值、成本、滑價、持倉時間），而不是只追 accuracy。  
   - CV 必須使用 **Purged K-Fold / Embargo**（避免資訊洩漏）。  
   - 所有特徵都要追溯「可用時間」（as-of timestamp），否則就是 look-ahead。  
3) **Overfitting 偵測是硬門檻**：對每一個「看起來很賺」的策略，都要做 Testing Set Overfitting 檢驗（多重比較/試誤偏誤），並用 **Deflated Sharpe / Prob. of backtest overfitting** 類型工具做降溫。  
4) **成本模型內建**：交易成本（手續費、期交稅/券商費、滑價、成交機率）不是事後補丁，是研究/回測/上線的同一套引擎。  
5) **策略不是單一神招**：永遠以「策略集群」思維：多 alpha、多週期、多訊號來源、多風控層，並用分群與相依性管理做組合配置。

### 0.2 系統原則（可上線、可維運）
沿用 v9：可靠性 > 新功能；SLO 驅動；事故是常態；權限/金鑰零信任；可回放=可修復。  
（v9 的 SRE/DR/安全/事故流程完整保留於 v10，並加上研究工廠的 SLO 與可回放。）

---

## 1) 最終目標的「端到端」藍圖（我在開發時必須映射到此）

### 1.1 Pipeline 分層
1) **Data Layer**：行情/五檔/成交/期權鏈/結算資訊 → 可靠入庫（帶時間戳、重放ID）。  
2) **Feature Layer**：以「可用時間」生成特徵（含 order-book microstructure / 波動/價量/籌碼 proxy）。  
3) **Label Layer**：用 financial labels（含 triple-barrier / time-stop / cost-aware）建立監督學習或策略評估標籤。  
4) **Research Layer**：  
   - Denoising / Detoning（去雜訊/去共同因子）  
   - 距離度量與最佳分群（找 regime / alpha families）  
   - Feature importance（找「可解釋」與「穩定」訊號）  
   - Walk-forward + Purged CV + Overfitting tests  
5) **Strategy Factory**（v8）：策略候選池 → 參數搜尋 → 壓縮成少數可部署候選（含 meta-labeling / risk allocation）。  
6) **Execution & Risk OS**（v6/v9）：Event-driven Exec FSM、OMS、風控總控、看門狗、Kill switch。  
7) **Observability & Incident OS**（v9）：SLO/告警/Runbook/回放/復原/資安。

### 1.2 TXF/MTX/TXO 特色（我必須內建）
- **交易所規則（TAIFEX）**：動態價格穩定措施（DPBM）、結算日與最後結算價計算、保證金與追繳、夜盤流動性、委託拒單行為。  
- **微結構**：夜盤點差、盤中流動性隨時段變化、開收盤跳動、極端行情的 reject storm。  
- **期權（TXO）**：到期、履約、assignment 機制、保證金模型、波動率風險與 gamma 風險。  
（本段的「規則」只是方向，實作上必須以 TAIFEX 官方文件/法規文字為準。）

---

## 2) v10 的新增核心：ML 理論探索框架（Machine Learning for Asset Managers）

> 目的不是「堆模型」，而是把 ML 當作**發現經濟/市場理論**的工具：找出在不同 regime 下仍成立的規律，並能被風控與執行系統承載。

### 2.1 Denoising & Detoning（去雜訊 / 去共同因子）
**用法（在 TMF）**  
- 對策略/訊號/特徵相關性矩陣做去雜訊（random matrix intuition），降低「假相關」造成的組合崩潰。  
- Detoning：去掉市場共同因子（例如大盤/波動共同成分），更容易看到「真正可分散的 alpha」。  
**落地**：  
- 用於 Strategy Factory 的候選集去重、以及 Risk Capital Allocation（避免同質化訊號同時爆炸）。  

### 2.2 Distance Metrics（距離度量，不只用 correlation）
**為什麼重要**：用錯距離=分群錯=組合配置錯。  
**落地**：  
- 以多種距離（如基於相關、互資訊、尾端依賴 proxy）建立策略相似度，再做 robust clustering。  

### 2.3 Optimal Clustering（最佳分群：Regime / Alpha 家族）
**目標**：把候選策略/特徵自動分成「可替代」與「可互補」兩類。  
**落地**：  
- 分群輸出：  
  - `alpha_family_id`（同家族不能同時加槓桿）  
  - `regime_tag`（某家族只在特定 regime 啟用）  

### 2.4 Financial Labels（金融標籤：回到交易本質）
**核心**：Label 不是 0/1 漲跌，而是「這筆交易在成本與風險下是否值得做」。  
**落地**（TXF/MTX）：  
- Triple-barrier：profit-take / stop-loss / time-stop（必須 cost-aware）。  
- 依持倉時間與交易成本，把 label 變成「期望值最大化」的代理目標。  
- 對高頻訊號：用 event-based bars（volume/dollar/imbalance）取代固定時間 bar。  

### 2.5 Feature Importance（特徵重要性：找穩定訊號）
**目標**：不是找「最強」，是找「最穩、最可解釋、最不依賴特定期間」的特徵。  
**落地**：  
- 對每個策略/模型：輸出 `fi_report`（含 permutation / SHAP 類型概念、以及在不同日期/不同 regime 的穩定度）。  
- **硬規則**：FI 不穩定（跨日期翻轉）→ 禁止上線（最多當 research-only）。  

### 2.6 Portfolio Construction（在 TMF 變成「策略組合配置」）
把「資產組合」觀念映射到「策略/訊號組合」：  
- 每個策略是一個「資產」，有其報酬分布、尾端風險、交易成本、容量上限。  
- 透過分群與去雜訊後的協方差/相依性，做 risk parity / volatility targeting / drawdown control。  
- **TXO 作為保險腿**：在極端 regime 用期權做 convex hedge（但必須把 theta 成本納入）。  

### 2.7 Testing Set Overfitting（測試集過度擬合）
**硬門檻**：任何「策略大賺」都必須做：  
- 多重比較調整（你試了多少組參數/多少策略）  
- Deflated Sharpe / backtest overfitting probability 的降溫  
- 以及「影子測試集」：把最近一段 data 完全不碰，用作最後一刀。  

---

## 3) TXF/MTX/TXO 的策略模組藍圖（Strategy Factory 必須輸出這些型別）

> v10 的策略不是「指標堆疊」，而是「可被風控承載、可被分群、可被配置」的模組。

### 3.1 Alpha 家族（我建議優先）
1) **開盤/收盤微結構**：開盤跳動、集合競價後的均衡回歸、午盤/尾盤流動性衰減。  
2) **動能與反轉的多週期混合**：  
   - 短週期：order-book imbalance / trade intensity  
   - 中週期：breakout / trend following  
   - 長週期：波動 regime 轉換（vol expansion/contraction）  
3) **波動率策略（TXO）**：  
   - 當波動風險溢酬存在：賣方策略 + 嚴格風控（gamma/跳空風險）  
   - 當極端風險升高：買方保護腿（convexity）  
4) **跨商品/跨合約結構**：  
   - TXF vs MTX 的流動性差異  
   - 不同到期月份的價差（calendar spread）與換月處理  
5) **事件驅動**：結算日、重大公告、台/美股期貨連動時段。

### 3.2 訊號工程（Feature Layer）
- 價量：VWAP 偏離、成交量加速度、range/ATR、波動率群聚。  
- 五檔：bid/ask depth、order-book imbalance、queue position proxy。  
- 期權鏈：IV term structure、skew、gamma exposure proxy、put/call 比例（注意資料可得性與時間戳）。  
- Regime：波動 regime、流動性 regime、趨勢 regime（用 clustering/hidden-state 思想做穩健分類）。

---

## 4) 風險控制層（Risk OS）：長期大賺小賠的唯一保證

### 4.1 四層風控（不可缺）
1) **交易前（Pre-trade）**：  
   - Max position / max leverage / max order rate / price band check  
   - 交易成本與滑價上限（超過就不下）  
2) **交易中（In-trade）**：  
   - 動態止損/移動停利/時間止損  
   - 異常行情降槓桿（vol targeting）  
3) **交易後（Post-trade）**：  
   - TCA（slippage、fill rate、reject rate）  
   - 策略健康分數（winrate 不是主指標，EV/尾端風險才是）  
4) **日內/跨日總控（Kill switch）**：  
   - 單日最大虧損（hard stop）  
   - 連續虧損/連續滑價爆炸（soft → hard）  
   - 報價中斷/回報異常（立即停機）  

### 4.2 Position sizing（不是猜，是系統）
- 以風險預算（risk budget）做 sizing：每筆交易最大風險、每策略最大風險、全系統最大風險。  
- 波動調整：vol 越高，部位越小；並在 regime 轉換時快速降槓桿。  
- 避免 Kelly 失控：可用 fractional Kelly 或 risk parity 思維，並加上 drawdown governor。

---

## 5) Execution Engine（OMS/Exec FSM/Watchdogs）

**核心**：交易策略可以普通，但執行系統不能普通。  
- Event-driven：Quote/Trade/OrderUpdate 都是事件；狀態機驅動。  
- Idempotency：任何重送不會造成重複下單。  
- Rate limiting：防 reject storm。  
- Watchdog：  
  - 行情斷線 > N 秒 → 立即停機或降級  
  - Order 回報延遲/缺失 → 降級/撤單/切換模式  
- Replay：任何 live 事故都要能用事件流重播重現。  

---

## 6) Research → Paper → Live 的 Gate（v7/v9 延伸到研究工廠）

### 6.1 Gate 規則（硬門檻）
- Research-only：可以冒險，但必須能重現與解釋。  
- Paper：必須通過 SMOKE + CANARY（含成本、含滑價模型、含斷線/拒單模擬）。  
- Live：必須通過 STRESS + PRELIVE（含事故演練、DR 演練、資安檢查、SLO 設定）。  

### 6.2 每日/每週固定產物
- `DAILY_REPORT`：策略 EV、尾端風險、TCA、SLO 達標。  
- `WEEKLY_REVIEW`：策略家族分布是否漂移、FI 穩定性、regime 漂移、過度擬合警報。  

---

## 7) 我需要你提供的「新增資料/論文/書」清單（強化 v10 的最有效方向）

你已提供：  
- López de Prado《Advances in Financial Machine Learning》  
- López de Prado《Machine Learning for Asset Managers》  
- Ernie Chan《Algorithmic Trading》  
- Kaufman《Trading Systems and Methods》  
（以及中文技術分析/量化書作為補充。）

若要再上到更強（但我建議從 v10 開始轉為「patch」而非一直升版），最值得補這些：

### 7.1 市場微結構 / 交易所機制
- 《Trading and Exchanges》Larry Harris（市場微結構的經典）  
- 《Market Microstructure Theory》Maureen O’Hara（更偏學術）  

### 7.2 執行與交易工程
- 《Algorithmic Trading and DMA》Barry Johnson（交易系統/執行工程）  
- 《High-Frequency Trading》Irene Aldridge（HFT/風控/微結構）  

### 7.3 系統化交易與風控（非常契合我們目標）
- 《Systematic Trading》Robert Carver（position sizing / risk targeting / 系統化流程）  
- 《The Evaluation and Optimization of Trading Strategies》Robert Pardo（回測與優化陷阱）  
- 《Evidence-Based Technical Analysis》David Aronson（過度擬合與統計檢驗）  

### 7.4 期權（TXO）必備
- 《Option Volatility & Pricing》Sheldon Natenberg（期權入門到實戰）  
- 《Volatility Trading》Euan Sinclair（波動交易與風控）  
- 《Dynamic Hedging》Nassim Taleb（對沖與風險直覺）  

---

## 8) 驗收步驟（逐步）/Acceptance Steps（主線視窗必照做）

> 這是「把 bible 變成行為」的清單：任何新模組上線前都要走完。

### 8.1 研究模組（Research）驗收
1) 確認資料有「可用時間」標記（as-of）。  
2) 產生 label（含成本/滑價/時間止損），並保存 label 版本與參數。  
3) 用 Purged K-Fold + embargo 跑 CV。  
4) 產出 FI 報告（含跨日期穩定性）。  
5) 做 overfitting 檢驗（多重比較降溫）。  
6) 生成 `RESEARCH_NOTE`：理論假設、反證條件、失效模式。

### 8.2 Paper 模式驗收
1) SMOKE：最小資料集 + 最小策略集跑通。  

   - **OFFICIAL Regression Suite（M2）**：Risk gates + Market-quality gates + Paper-live integration smoke。
     - 規格/步驟：`docs/ops/M2_REGRESSION_SUITE_BIBLE_v1.md`（必跑；輸出 log + GOV snapshot + sha256 sidecar）
2) CANARY：小風險預算、限制交易頻率，連跑 N 天。  
3) 故障注入：行情斷線、回報延遲、reject storm、time skew。  
4) TCA 檢查：滑價、fill rate、reject rate 在 SLO 範圍內。  

### 8.3 Live 上線驗收
1) PRELIVE：事故演練（Runbook）、DR 演練（備援/回復）、金鑰輪替演練。  
2) 風控硬門檻啟用：每日最大虧損、連續虧損、最大曝險。  
3) 開啟告警：SLO 破壞、異常成交、異常滑價、異常拒單。  
4) 上線後 1 週：每日 review + 必要時自動降級/停機。

---

## 9) v9 內容保留宣告
v10 以 v9 為底：SRE/DR/資安/事故OS/回放/回滾/變更管控全部保留；本文件只新增「研究工廠」與「ML 理論探索」硬規則，並把 TXF/TXO 的在地化要點更明確化。








