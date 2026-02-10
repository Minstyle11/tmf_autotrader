# 專案進度總覽（自動計算）
- 更新時間：2026-02-10 09:05:32
- 專案總完成度：23.3% （已完成 24 / 103 項）

**專案總完成度 / Overall completion:** 23.3%（已完成 24 / 103 項；未完成 79 項）

<!-- AUTO:PROGRESS_BEGIN -->
- 更新時間：2026-02-10 09:05:32
- **TOTAL_TASKS:** 103
- **DONE_TASKS:** 24
- **DOING_TASKS:** 2
- **BLOCKED_TASKS:** 0
- **PCT:** 23.3%
<!-- AUTO:PROGRESS_END -->


## 里程碑完成度
- M0 Foundations：100.0% （已完成 4 / 4）
- M1 Sim + Cost Model：100.0% （已完成 3 / 3）
- M2 Risk Engine v1 (Risk First)：100.0% （已完成 3 / 3）
- M3 Strategy Base + Paper Live：42.9% （已完成 3 / 7）

## 說明（快速讀法）
- 看「專案總完成度」掌握全局；看「里程碑完成度」掌握目前在哪一段。
- [ ] 進行中、[!] 阻塞、[x] 已完成。

# TMF AutoTrader Project Board (OFFICIAL)

## Status Legend
- [ ] TODO
- [~] DOING
- [x] DONE
- [!] BLOCKED



## Bible Linkage (OFFICIAL-LOCKED)

- Last refresh: 2026-02-06T08:18:13
- `TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18.md` sha256=`37510ad07149bb96fdd89c1e245cafc6dc4cef9cb9e53954920b94f19a9638da` headings=303
- `TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18_1_PATCH.md` sha256=`e4f51bf4a691987d343e53575244b6da13e5ef4cc20867b7e039e3370f377b71` headings=25
- `TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18_2_PATCH.md` sha256=`39714f5adf840b6cae8a67a8f81d2c5e258017820e9e2c21651422b83669d78b` headings=31

## Milestones
### M0 Foundations
- [x] Create repo skeleton + board + bible system + backup framework
- [x] Broker connectivity: Shioaji login + quote subscribe (TMF/TX/MTX + 2330/2317/2454) + raw event recorder
- [x] Data store: schema v1 (events, bars, trades, orders, fills) + rotation
- [x] Ops: runbook v1 + healthcheck v1 + auto-restart v1
### M1 Sim + Cost Model
- [x] TAIFEX fee/tax model v1 (exchange fees + futures transaction tax + broker fee configurable)
- [x] Paper OMS + matching engine v1 (market/limit, partial fill if possible)
- [x] Slippage model v1 (conservative)

### M2 Risk Engine v1 (Risk First)
- [x] Pre-trade gates (DONE: stop-required + per-trade max loss + daily max loss + consecutive-loss cooldown + market-quality gates (spread/ATR/liquidity) + regressions; DONE: wired real market_metrics source (bidask->DB->market_metrics) + paper-live can be strict (policy pending))
- [x] BidAsk schema normalization (bid/ask scalars derived from level-1 arrays; recorder+DB+market_metrics smoke PASS)
- [x] In-trade controls (SL/TS/breakeven, time-stop, session-aware rules)
- [x] System safety (disconnect handling, session state machine, expiry-day guards)

### M3 Strategy Base + Paper Live
- [~] Trend strategy v1 (dual-side) + attribution logging
- [ ] Mean-reversion v1 (dual-side) + attribution logging
- [ ] Daily report v1 + auto diagnostics

## Always-On Bibles (must obey)
- docs/bibles/TMF_AUTOTRADER_CONSTITUTION_BIBLE_v1.md  (CONSTITUTION / MUST-OBEY)
- docs/bibles/TMF_AUTOTRADER_CONSTITUTION_BIBLE_v1.md.sha256.txt
- docs/bibles/TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18.md  (ONE-TRUTH / OVERRIDES ALL)
- docs/bibles/TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18.md.sha256.txt

> 規則鎖定：任何規則/流程/優先序如與 v18 衝突，一律以 v18 為準。


## V18 Alignment Status
- last_sweep_json: `docs/board/V18_ALIGN_SWEEP_REPORT_20260201_203308.json`
- last_scaffold_report: `docs/board/V18_SCAFFOLD_REPORT_20260201_203451.md`
- missing_dirs_before: 12
- missing_files_before: 57
- created_dirs: 12
- created_files: 57
- py_compile_errors: 0
- next: implement v18 mainline OS modules (spec-diff stopper / reject taxonomy+policy / reconcile / replay / latency+backpressure / cost-model OS / stress battery / auto-remediation / drills).

## V18 - Execution Reject Taxonomy & Policy (M3)

- [x] execution/reject_taxonomy.py (decision_from_verdict + policy mapping)
- [x] execution/reject_policy.yaml (JSON-compatible YAML; no external deps)
- [x] scripts/m3_regression_reject_policy_v1.sh (regression)
- [x] Wire decision into PaperOMSRiskSafetyWrapperV1 / live runner (DONE: reject_policy + decision_from_verdict wired; m3 regression PASS; paper-live smoke PASS)

> 2026-02-02 22:27:20 OFFICIAL: M2 gates closure verified (risk+market-quality+integration smoke PASS); synthetic bidask filtered; offline smoke flag added.

<!-- AUTO:PATCH_TASKS_BEGIN -->

## v18.1 / v18.2 補強條款 → 任務清單（自動生成） / Patch-to-Tasks (AUTO)

### vv18_1 條款落地任務 / vv18_1 Compliance Tasks (AUTO)

- 說明：由程式自動擷取 `TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18_1_PATCH.md` 的標題與強制詞條款；完成後勾選 `- [x]`。如需調整映射，請走 OFFICIAL v18.x patch。

- [ ] [TASK:M8-V18_1-01-74a39141] **3) **自動學習/自我改進的安全治理**（drift/非平穩/線上學習 = 必須“可控、可回退、可凍結”） / 3) **自動學習/自我改進的安全治理**（drift/非平穩/線上學習 = 必須“可控、可回退、可凍結”）**
- [ ] [TASK:M8-V18_1-02-3c66f4ad] **A) 研究/回測：統計嚴謹性「硬闖關」補強（必做） / A) 研究/回測：統計嚴謹性「硬闖關」補強（必做）**
- [ ] [TASK:M8-V18_1-03-cd700180] **A1) v18 原本的 Research Gate 再加一層：**DSR / PBO / Reality Check****
- [ ] [TASK:M8-V18_1-04-082e41be] **因此 v18 的研究闖關必須新增以下三個“硬闖關”： / 因此 v18 的研究闖關必須新增以下三個“硬闖關”：**
- [ ] [TASK:M8-V18_1-05-46121727] **A2) 研究輸出改成「三件套」才能進下一關 / A2) 研究輸出改成「三件套」才能進下一關**
- [ ] [TASK:M8-V18_1-06-f73e35a1] **每個策略候選（含參數集）必須輸出： / 每個策略候選（含參數集）必須輸出：**
- [ ] [TASK:M8-V18_1-07-7a95b6ce] **B) TAIFEX 在地交易所硬限制：必做的「送單前」驗證（避免 Rejected / 錯單）**
- [ ] [TASK:M8-V18_1-08-ee50c910] **B1) Order Size Limits（最容易踩雷） / B1) Order Size Limits（最容易踩雷）**
- [ ] [TASK:M8-V18_1-09-7fd37f6a] **TAIFEX 對不同委託型態有每筆口數上限；尤其 **Market order 在日盤與夜盤上限不同**。送單前必須檢查。 / TAIFEX 對不同委託型態有每筆口數上限；尤其 **Market order 在日盤與夜盤上限不同**。送單前必須檢查。**
- [ ] [TASK:M8-V18_1-10-04ed66fc] **=> v18 的 OrderGuard 必須把 **TAIFEX order-size-limit 規則**做成「硬擋」：超過就拆單或拒單（依 policy）。 / => v18 的 OrderGuard 必須把 **TAIFEX order-size-limit 規則**做成「硬擋」：超過就拆單或拒單（依 policy）。**
- [ ] [TASK:M8-V18_1-11-8396db96] **B2) MWP（Market with Protection）一定要用“交易所定義” / B2) MWP（Market with Protection）一定要用“交易所定義”**
- [ ] [TASK:M8-V18_1-12-f3030576] **=> 你的滑價/成交概率/拒單風險評估，必須按交易所定義建模；不能只用“理想化市價單”。 / => 你的滑價/成交概率/拒單風險評估，必須按交易所定義建模；不能只用“理想化市價單”。**
- [ ] [TASK:M8-V18_1-13-753b031d] **B3) Price limit / dynamic mechanisms：要把“交易所保護”當成 regime**
- [ ] [TASK:M8-V18_1-14-48df5392] **=> v18 的 Regime Engine（或 market regime）必須把「靠近漲跌停/擴大/動態機制觸發」當成**禁做或降風險模式**，至少做到： / => v18 的 Regime Engine（或 market regime）必須把「靠近漲跌停/擴大/動態機制觸發」當成**禁做或降風險模式**，至少做到：**
- [ ] [TASK:M8-V18_1-15-f1808f9b] **C) Shioaji / 永豐金：事件真相源的「更嚴格」落地規則**
- [ ] [TASK:M8-V18_1-16-0ecf651d] **C1) Deal 事件可能先於 Order 事件（必須容忍 out-of-order） / C1) Deal 事件可能先於 Order 事件（必須容忍 out-of-order）**
- [ ] [TASK:M8-V18_1-17-b0498bb4] **=> v18 的 Event Sourcing 必須保證： / => v18 的 Event Sourcing 必須保證：**
- [ ] [TASK:M8-V18_1-18-5037f759] **C2) subscribe_trade 必須視為“可關閉但不建議” / C2) subscribe_trade 必須視為“可關閉但不建議”**
- [ ] [TASK:M8-V18_1-19-0b3c6dba] **=> v18.1：除非是 research-only sandbox，否則 **強制 subscribe_trade=True**。 / => v18.1：除非是 research-only sandbox，否則 **強制 subscribe_trade=True**。**
- [ ] [TASK:M8-V18_1-20-2d99d013] **D) 自主學習/自我改進：加上「安全護欄」才能准許進 live / D) 自主學習/自我改進：加上「安全護欄」才能准許進 live**
- [ ] [TASK:M8-V18_1-21-3b3d31f6] **D1) “學習”只能在三種模式中切換（硬規則） / D1) “學習”只能在三種模式中切換（硬規則）**
- [ ] [TASK:M8-V18_1-22-740a564e] **D2) Drift 必須先被量化：Concept drift detector + 失效處置 / D2) Drift 必須先被量化：Concept drift detector + 失效處置**
- [ ] [TASK:M8-V18_1-23-25e5b22d] **D3) Safe RL / Risk-aware bandits：只允許“有約束”的學習**
- [ ] [TASK:M8-V18_1-24-9c661ec2] **必須採用 **風險約束**（如 CVaR/mean-variance constraints）或安全 RL 的 constraint formulation。 / 必須採用 **風險約束**（如 CVaR/mean-variance constraints）或安全 RL 的 constraint formulation。**
- [ ] [TASK:M8-V18_1-25-fe8da918] **E) 事故文化補強：交易系統 = SRE 系統 / E) 事故文化補強：交易系統 = SRE 系統**
- [ ] [TASK:M8-V18_1-26-88bf2570] **E1) 強制 Blameless Postmortem（但要“可執行改進”） / E1) 強制 Blameless Postmortem（但要“可執行改進”）**
- [ ] [TASK:M8-V18_1-27-1c3f6dbc] **F) v18.1 最小落地工作清單（主線助理拿來做 Roadmap 切片） / F) v18.1 最小落地工作清單（主線助理拿來做 Roadmap 切片）**
- [ ] [TASK:M8-V18_1-28-ad490f5f] **驗收步驟（逐步）/ Acceptance Steps / 驗收步驟（逐步）/ Acceptance Steps**
- [ ] [TASK:M8-V18_1-29-4bcdeada] **[A] 統計嚴謹性 Gate（DSR/PBO/RealityCheck） / [A] 統計嚴謹性 Gate（DSR/PBO/RealityCheck）**
- [ ] [TASK:M8-V18_1-30-068690e6] **[B] TAIFEX OrderGuard（硬擋） / [B] TAIFEX OrderGuard（硬擋）**
- [ ] [TASK:M8-V18_1-31-f80c7aa3] **[C] Shioaji 事件亂序容忍 / [C] Shioaji 事件亂序容忍**
- [ ] [TASK:M8-V18_1-32-80ce6e5a] **[D] Learning modes（Frozen/Shadow/Promote） / [D] Learning modes（Frozen/Shadow/Promote）**
- [ ] [TASK:M8-V18_1-33-ac7d327f] **3. Promote：只能在 release window，且 must canary；若 drift/風險觸發 → 自動 rollback 回 Frozen。 / 3. Promote：只能在 release window，且 must canary；若 drift/風險觸發 → 自動 rollback 回 Frozen。**
- [ ] [TASK:M8-V18_1-34-0879a590] **[E] Postmortem / [E] Postmortem**
- [ ] [TASK:M8-V18_1-35-a5f392a3] **Patch 引用（主線助理使用的“外部真相錨點”） / Patch 引用（主線助理使用的“外部真相錨點”）**

### vv18_2 條款落地任務 / vv18_2 Compliance Tasks (AUTO)

- 說明：由程式自動擷取 `TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18_2_PATCH.md` 的標題與強制詞條款；完成後勾選 `- [x]`。如需調整映射，請走 OFFICIAL v18.x patch。

- [ ] [TASK:M8-V18_2-01-c090bde5] **0) 本 Patch 依據與新增參考來源（高負載摘要） / 0) 本 Patch 依據與新增參考來源（高負載摘要）**
- [ ] [TASK:M8-V18_2-02-e77e81fa] **0.1 官方/產業規範（需納入程式設計假設） / 0.1 官方/產業規範（需納入程式設計假設）**
- [ ] [TASK:M8-V18_2-03-398d1de8] ****TAIFEX 動態價格穩定措施（Dynamic Price Banding Mechanism, DPBM）**：當成交模擬價超過上下限，交易所會直接拒單；策略與執行層必須能偵測/處理被拒與重新報價（含撤單/重掛/降價/退避）。citeturn0search0turn0search4turn0sear... / **TAIFEX 動態價格穩定措施（Dynamic Price Banding Mechanism, DPBM）**：當成交模擬價超過上下限，交易所會直接拒單；策略與執行層必須能偵測/處理被拒與重新報價（含撤單/重掛/降價/退避）。citeturn0search0turn0search4turn0sear...**
- [ ] [TASK:M8-V18_2-04-3a2fb357] **0.2 執行端（永豐金 Shioaji） / 0.2 執行端（永豐金 Shioaji）**
- [ ] [TASK:M8-V18_2-05-0f5fd98c] **Shioaji 的 **Streaming Market Data / subscribe(tick,bidask)**、quote callback、以及 quote-binding 等高階用法，必須被納入「報價中斷偵測、延遲監控、撮合保護、與策略節流」。citeturn0search1turn0sear...**
- [ ] [TASK:M8-V18_2-06-e5e57729] **0.3 回測/研究誠實性（AFML/De Prado） / 0.3 回測/研究誠實性（AFML/De Prado）**
- [ ] [TASK:M8-V18_2-07-6c4e07b2] **1) 期望值（Expected Return）建模：把「策略好不好」從回測曲線拉回可驗證的來源 / 1) 期望值（Expected Return）建模：把「策略好不好」從回測曲線拉回可驗證的來源**
- [ ] [TASK:M8-V18_2-08-f7be1b4f] **1.1 交易型期望值的三層分解（必須在研究報告中固定輸出） / 1.1 交易型期望值的三層分解（必須在研究報告中固定輸出）**
- [ ] [TASK:M8-V18_2-09-0817c011] **1.2 期望值估計的「不許偷吃」規格 / 1.2 期望值估計的「不許偷吃」規格**
- [ ] [TASK:M8-V18_2-10-d15db248] ****多重檢定控制**：參數 sweep 不是越多越好；必須有「白紙假說」與「淘汰率」。使用 purged CV / CPCV 才能把過擬合壓下來。citeturn0search3turn0search19**
- [ ] [TASK:M8-V18_2-11-57ad11b1] **2) 市場微結構（Market Microstructure）：把「價差/五檔/委託簿」納入策略與執行一體化 / 2) 市場微結構（Market Microstructure）：把「價差/五檔/委託簿」納入策略與執行一體化**
- [ ] [TASK:M8-V18_2-12-cd2e8d4b] **2.1 必備的「微結構資料欄位」（若 Shioaji 可得，優先用；不可得則以 proxy） / 2.1 必備的「微結構資料欄位」（若 Shioaji 可得，優先用；不可得則以 proxy）**
- [ ] [TASK:M8-V18_2-13-516fc2d6] **2.2 兩個「必做」的微結構模型（先簡後繁） / 2.2 兩個「必做」的微結構模型（先簡後繁）**
- [ ] [TASK:M8-V18_2-14-0ed3c289] **必須把 DPBM 拒單視為「額外成本風險」，並輸出 rejection 的條件統計。citeturn0search0turn0search12 / 必須把 DPBM 拒單視為「額外成本風險」，並輸出 rejection 的條件統計。citeturn0search0turn0search12**
- [ ] [TASK:M8-V18_2-15-04fd3a40] **3) 選擇權/波動率（Options & Volatility）：用來「擴展策略宇宙」與「尾部風險治理」 / 3) 選擇權/波動率（Options & Volatility）：用來「擴展策略宇宙」與「尾部風險治理」**
- [ ] [TASK:M8-V18_2-16-9f71949c] **3.1 波動率必備觀念（要變成模組，不只是知識） / 3.1 波動率必備觀念（要變成模組，不只是知識）**
- [ ] [TASK:M8-V18_2-17-db194ed3] **3.2 期貨主線的「最低限度」波動率整合（不做選擇權也要做） / 3.2 期貨主線的「最低限度」波動率整合（不做選擇權也要做）**
- [ ] [TASK:M8-V18_2-18-d5ae1de0] **`signal_confidence` 必須被 `vol_regime` 調制（高波動時假訊號更多、滑價更大） / `signal_confidence` 必須被 `vol_regime` 調制（高波動時假訊號更多、滑價更大）**
- [ ] [TASK:M8-V18_2-19-0fef92d6] **3.3 若未來要納入選擇權（先把骨架在 v18 主線留好） / 3.3 若未來要納入選擇權（先把骨架在 v18 主線留好）**
- [ ] [TASK:M8-V18_2-20-89249a37] **4) 槓桿/保證金/倉位：把「會賺」變成「活得久」 / 4) 槓桿/保證金/倉位：把「會賺」變成「活得久」**
- [ ] [TASK:M8-V18_2-21-213ccb3c] **4.1 倉位 sizing 的兩階段門檻（Hard Gate） / 4.1 倉位 sizing 的兩階段門檻（Hard Gate）**
- [ ] [TASK:M8-V18_2-22-150f6ba5] **但必須有：vol targeting、drawdown throttle、consecutive loss cooldown、與日內風險重置規則（v18 已有，這裡要求必須與 sizing 綁死） / 但必須有：vol targeting、drawdown throttle、consecutive loss cooldown、與日內風險重置規則（v18 已有，這裡要求必須與 sizing 綁死）**
- [ ] [TASK:M8-V18_2-23-2da6dbc7] **4.2 Kelly / Fractional Kelly 的使用準則（避免自殺）**
- [ ] [TASK:M8-V18_2-24-7445c291] **Kelly 只能當「上限參考」，不可直接全額套用；必須用 **fractional Kelly**，並且用保守估計（下分位的勝率/報酬比）做輸入。 / Kelly 只能當「上限參考」，不可直接全額套用；必須用 **fractional Kelly**，並且用保守估計（下分位的勝率/報酬比）做輸入。**
- [ ] [TASK:M8-V18_2-25-57a31f51] **如果策略是 regime-sensitive（大多數都是），Kelly 估計必須分 regime 做，且要有 shrinkage（向整體均值收縮）。 / 如果策略是 regime-sensitive（大多數都是），Kelly 估計必須分 regime 做，且要有 shrinkage（向整體均值收縮）。**
- [ ] [TASK:M8-V18_2-26-ed0bfb03] **5) 執行與風控：把「交易所拒單/斷線/延遲」納入 state machine，而不是例外處理 / 5) 執行與風控：把「交易所拒單/斷線/延遲」納入 state machine，而不是例外處理**
- [ ] [TASK:M8-V18_2-27-ac67d177] **5.1 DPBM / 交易所保護機制的必備狀態機**
- [ ] [TASK:M8-V18_2-28-3377083f] **5.2 Shioaji 串流與斷線治理（必做） / 5.2 Shioaji 串流與斷線治理（必做）**
- [ ] [TASK:M8-V18_2-29-460263dd] **5.3 機構級 pre-trade risk control 清單（必備） / 5.3 機構級 pre-trade risk control 清單（必備）**
- [ ] [TASK:M8-V18_2-30-c74dfc09] **6) 自主學習/自我改進：把「研究→上線→回饋」變成可重播的閉環 / 6) 自主學習/自我改進：把「研究→上線→回饋」變成可重播的閉環**
- [ ] [TASK:M8-V18_2-31-420add21] **6.1 最小可行的自我改進（v18 主線必須內建） / 6.1 最小可行的自我改進（v18 主線必須內建）**
- [ ] [TASK:M8-V18_2-32-493c3366] **任何「自動調參」都必須在 paper 環境先跑過 **purged CV + walk-forward**，再進 canary。citeturn0search3turn0search15 / 任何「自動調參」都必須在 paper 環境先跑過 **purged CV + walk-forward**，再進 canary。citeturn0search3turn0search15**
- [ ] [TASK:M8-V18_2-33-9774ddad] **7) 對 v18 的「精準修改建議」（不改也能先上線，但建議排進 v18.x 主線） / 7) 對 v18 的「精準修改建議」（不改也能先上線，但建議排進 v18.x 主線）**
- [ ] [TASK:M8-V18_2-34-3533e0a6] **8) 驗收步驟（逐步） / 8) 驗收步驟（逐步）**
- [ ] [TASK:M8-V18_2-35-b3b01279] **8.1 文件驗收（5 分鐘） / 8.1 文件驗收（5 分鐘）**
- [ ] [TASK:M8-V18_2-36-8c377b20] **8.2 研究端驗收（半天～1 天，依你現有框架） / 8.2 研究端驗收（半天～1 天，依你現有框架）**
- [ ] [TASK:M8-V18_2-37-7a00e451] **8.3 執行端驗收（paper live） / 8.3 執行端驗收（paper live）**
- [ ] [TASK:M8-V18_2-38-cfcb33a6] **9) 後續若要再更強：我建議你「優先補」的資料/書（若你願意再提供） / 9) 後續若要再更強：我建議你「優先補」的資料/書（若你願意再提供）**

<!-- AUTO:PATCH_TASKS_END -->
- [x] [TASK:PM] Daily Finance Close Pack AUTO daily agent v1 + kickstart smoke (2026-02-04) (LaunchAgent=com.tmf_autotrader.daily_finance_close_pack_v1)
## AUTOLOG (append-only)
- [2026-02-06T23:00:40] DB sanity autoclose done (kept latest open per symbol); open_trades_cnt should now be 1 (TMF).


---

## Progress Log (append-only)

### 2026-02-06
- [x] RiskEngineV1: allow reduce-only close to bypass strict stop requirement (stop_reduceonly_bypass=1)
- [x] RiskEngineV1: derive entry_price for MARKET/reduce-only when price is None (use meta.ref_price, else bid/ask)
- [x] DB sanity: autoclose extra open trades (keep latest open per symbol); backup created: runtime/data/tmf_autotrader_v1.sqlite3.bak_sanity_autoclose_20260206_225703
- [~] Wrapper return-type hardening: add TypeGuard/TypedDict (Order | RejectedOrder) and enforce caller-side match guard
- [ ] Smoke scripts: never call PaperOMS.match() on REJECT dict; gate by is_order_obj / is_accepted_order()

- [2026-02-06 23:16] (DONE) PaperOMS.match hardguard: reject-dict -> TypeError (prevents AttributeError; clarifies caller contract)

## Recent Updates
- [2026-02-06 23:30] 2026-02-06 run_paper_live_v1: guard wrapper REJECTED dict before oms.match() (py_compile OK)

### 2026-02-06 23:34:57 Recent Update
- [x] paper-live-smoke: smoke_ok=True; SAFETY_FEED_STALE → COOLDOWN behavior verified
- [x] PaperOMS.match: typeguard added (reject dict is not matchable; raises clear TypeError)
- [x] run_paper_live_v1: match() only when wrapper returns Order (not REJECTED dict)
- [x] DB sanity: autoclose historical open trades (keep latest open per symbol)


- [x] 2026-02-07 00:26:03 smoke suite v1 added: scripts/run_paper_live_smoke_suite_v1.py (isolated DB copy, clears cooldown)

## AUTOLOG（TMF_AUTO / append-only）
- [2026-02-07 11:58:16] ✅ HEALTH_CHECKS: added column `health_checks.kind` + backfilled from `check_name`
- [2026-02-07 11:58:16] ✅ SMOKE_SUITE: patched scripts/run_paper_live_smoke_suite_v1.py to persist kind correctly (syntax fixed; py_compile OK)
- [2026-02-07 11:58:16] ✅ LaunchAgent: com.tmf_autotrader.paper_smoke_suite_v1 enabled; StartCalendarInterval=16:20; RunAtLoad=false
- [2026-02-07 11:58:16] ✅ Bible: docs/ops/HEALTH_CHECKS_KIND_AND_SMOKE_SUITE_BIBLE_v1.md (+ sha256) created

