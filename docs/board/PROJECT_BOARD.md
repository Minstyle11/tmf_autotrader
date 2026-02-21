# 專案進度總覽（自動計算）

<!-- AUTO_PROGRESS_START -->
**專案總完成度 / Overall completion:** 30.0%（已完成 24 / 80 項；未完成 56 項）

- done   : 24
- doing  : 0
- blocked: 0
- todo   : 56
- invalid_like: 0
<!-- AUTO_PROGRESS_END -->
**專案總完成度 / Overall completion:** 30.0%（已完成 24 / 80 項；未完成 56 項）

- 更新時間：2026-02-21 10:40:06
- 專案總完成度：30.0% （已完成 24 / 80 項；TODO 56 / DOING 0 / BLOCKED 0）

<!-- AUTO:PROGRESS_BEGIN -->
- **TOTAL:** 80
- **TOTAL_TASKS:** 80
- **TODO:** 56
- **DOING:** 0
- **DONE:** 24
- **DONE_TASKS:** 24
- **BLOCKED:** 0
- **PCT:** 30.0%
- **LAST_BOARD_UPDATE_AT:** 2026-02-21 10:40:06
<!-- AUTO:PROGRESS_END -->
## 里程碑完成度
- M0 Foundations：100.0% （已完成 4 / 4）
- M1 Sim + Cost Model：100.0% （已完成 3 / 3）
- M2 Risk Engine v1 (Risk First)：100.0% （已完成 3 / 3）
- M3 Strategy Base + Paper Live：42.9% （已完成 3 / 7）

## 說明（快速讀法）
- 進行中、[!] 阻塞、[x] 已完成。

# TMF AutoTrader Project Board (OFFICIAL)


## Status Legend
- ( ) TODO
- (~) DOING
- DONE
- (!) BLOCKED


## Bible Linkage (OFFICIAL-LOCKED)

- Last refresh: 2026-02-06T08:18:13
- `TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18.md` sha256=`37510ad07149bb96fdd89c1e245cafc6dc4cef9cb9e53954920b94f19a9638da` headings=303
- `TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18_1_PATCH.md` sha256=`e4f51bf4a691987d343e53575244b6da13e5ef4cc20867b7e039e3370f377b71` headings=25
- `TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18_2_PATCH.md` sha256=`39714f5adf840b6cae8a67a8f81d2c5e258017820e9e2c21651422b83669d78b` headings=31

## OS Modules — Completed (Auto)
- [x] [TASK:M3-REPLAYOS-DRIFT-2e3de863] **Replay OS drift taxonomy (event-order/missing/parse) + artifacted report** (writes replay_report_latest.json/.md with diagnostics+drift_codes; gated by ops_audit_hardgate_v1)

## Milestones
### M0 Foundations
- [x] [TASK:M0-e0f96880] Create repo skeleton + board + bible system + backup framework
- [x] [TASK:M0-10e13b4f] Broker connectivity: Shioaji login + quote subscribe (TMF/TX/MTX + 2330/2317/2454) + raw event recorder
- [x] [TASK:M0-5737d1e6] Data store: schema v1 (events, bars, trades, orders, fills) + rotation
- [x] [TASK:MISC-cd010ea0] Ops: runbook v1 + healthcheck v1 + auto-restart v1
### M1 Sim + Cost Model
- [x] [TASK:M1-ec5562d3] TAIFEX fee/tax model v1 (exchange fees + futures transaction tax + broker fee configurable)
- [x] [TASK:M1-6664639c] Paper OMS + matching engine v1 (market/limit, partial fill if possible)
- [x] [TASK:M1-36095ef6] Slippage model v1 (conservative)

### M2 Risk Engine v1 (Risk First)
- [x] [TASK:M2-a9935a52] Pre-trade gates (DONE: stop-required + per-trade max loss + daily max loss + consecutive-loss cooldown + market-quality gates (spread/ATR/liquidity) + regressions; DONE: wired real market_metrics source (bidask->DB->market_metrics) + paper-live can be strict (policy pending))
- [x] [TASK:M2-18c47e4c] BidAsk schema normalization (bid/ask scalars derived from level-1 arrays; recorder+DB+market_metrics smoke PASS)
- [x] [TASK:M2-4f83a238] In-trade controls (SL/TS/breakeven, time-stop, session-aware rules)
- [x] [TASK:MISC-6ec017cf] System safety (disconnect handling, session state machine, expiry-day guards)

### M3 Strategy Base + Paper Live
- [x] [TASK:M3-09a46d89] Trend strategy v1 (dual-side) + attribution logging
- [x] [TASK:M3-557c7247] Mean-reversion v1 (dual-side) + attribution logging
- [x] [TASK:M3-fee5f203] Daily report v1 + auto diagnostics (DONE: build_daily_report_v1 OK; DR_2026-02-12 md/json + sha256)

- [x] [TASK:M3-OS-1a2f3c4d] Latency+Backpressure OS module v1 (queue/lag/backpressure + throttle)
- [x] [TASK:M3-OS-2b3c4d5e] CostModel OS module v1 (fees/slippage sanity + execution-cost telemetry)
- [x] [TASK:M3-OS-3c4d5e6f] Stress Battery / Chaos Drills v1 (disconnect/latency/spread-spike + replay)
- [x] [TASK:M3-OS-4d5e6f70] Auto-Remediation + Runbook Drills v1 (auto-restart/kill-switch drill + evidence)

## Always-On Bibles (must obey)
- docs/ops/PROJECT_BOARD_AUTOSYNC_BIBLE_v1.md  (BOARD AUTOSYNC / MUST-OBEY)
- docs/ops/PROJECT_BOARD_AUTOSYNC_BIBLE_v1.md.sha256.txt
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
- next: implement v18 mainline OS modules (latency+backpressure / cost-model OS / stress battery / auto-remediation / drills).

## V18 - Execution Reject Taxonomy & Policy (M3)

- [x] [TASK:M3-REJECT-229a977a] execution/reject_taxonomy.py (decision_from_verdict + policy mapping)
- [x] [TASK:M3-REJECT-171b1e47] execution/reject_policy.yaml (JSON-compatible YAML; no external deps)
- [x] [TASK:M3-REJECT-5c17af4e] scripts/m3_regression_reject_policy_v1.sh (regression)
- [x] [TASK:M3-REJECT-ca288b87] Wire decision into PaperOMSRiskSafetyWrapperV1 / live runner (DONE: reject_policy + decision_from_verdict wired; m3 regression PASS; paper-live smoke PASS)

> 2026-02-02 22:27:20 OFFICIAL: M2 gates closure verified (risk+market-quality+integration smoke PASS); synthetic bidask filtered; offline smoke flag added.


- [x] [TASK:PM] Daily Finance Close Pack AUTO daily agent v1 + kickstart smoke (2026-02-04) (LaunchAgent=com.tmf_autotrader.daily_finance_close_pack_v1)
## AUTOLOG (append-only)
- [2026-02-06T23:00:40] DB sanity autoclose done (kept latest open per symbol); open_trades_cnt should now be 1 (TMF).


---

## Progress Log (append-only)

### 2026-02-06
- ✅ RiskEngineV1: allow reduce-only close to bypass strict stop requirement (stop_reduceonly_bypass=1)
- ✅ RiskEngineV1: derive entry_price for MARKET/reduce-only when price is None (use meta.ref_price, else bid/ask)
- ✅ DB sanity: autoclose extra open trades (keep latest open per symbol); backup created: runtime/data/tmf_autotrader_v1.sqlite3.bak_sanity_autoclose_20260206_225703
- ✅ Wrapper return-type hardening: add TypeGuard/TypedDict (Order | RejectedOrder) and enforce caller-side match guard
- ✅ Smoke scripts: never call PaperOMS.match() on REJECT dict; gate by is_order_obj / is_accepted_order()
- [2026-02-06 23:16] (DONE) PaperOMS.match hardguard: reject-dict -> TypeError (prevents AttributeError; clarifies caller contract)

## Recent Updates
- [2026-02-06 23:30] 2026-02-06 run_paper_live_v1: guard wrapper REJECTED dict before oms.match() (py_compile OK)

### 2026-02-06 23:34:57 Recent Update
- ✅ paper-live-smoke: smoke_ok=True; SAFETY_FEED_STALE → COOLDOWN behavior verified
- ✅ PaperOMS.match: typeguard added (reject dict is not matchable; raises clear TypeError)
- ✅ run_paper_live_v1: match() only when wrapper returns Order (not REJECTED dict)
- ✅ DB sanity: autoclose historical open trades (keep latest open per symbol)


- ✅ 2026-02-07 00:26:03 smoke suite v1 added: scripts/run_paper_live_smoke_suite_v1.py (isolated DB copy, clears cooldown)

## AUTOLOG（TMF_AUTO / append-only）
- [2026-02-07 11:58:16] ✅ HEALTH_CHECKS: added column `health_checks.kind` + backfilled from `check_name`
- [2026-02-07 11:58:16] ✅ SMOKE_SUITE: patched scripts/run_paper_live_smoke_suite_v1.py to persist kind correctly (syntax fixed; py_compile OK)
- [2026-02-07 11:58:16] ✅ LaunchAgent: com.tmf_autotrader.paper_smoke_suite_v1 enabled; StartCalendarInterval=16:20; RunAtLoad=false
- [2026-02-07 11:58:16] ✅ Bible: docs/ops/HEALTH_CHECKS_KIND_AND_SMOKE_SUITE_BIBLE_v1.md (+ sha256) created

## v18.x Patch Tasks (AUTO)
<!-- AUTO_M8_PATCH_TASKS_BEGIN -->
<!-- generated_at: 2026-02-20T23:59:40 -->
<!-- AUTO_M8_PATCH_TASKS_END -->
\n\n<!-- AUTO:M8_PATCH_TASKS_BEGIN -->



- 說明：由程式自動擷取 `TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18_1_PATCH.md` 的標題與強制詞條款；完成後勾選 [x]。如需調整映射，請走 OFFICIAL v18.x patch。



- 說明：由程式自動擷取 `TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18_2_PATCH.md` 的標題與強制詞條款；完成後勾選 [x]。如需調整映射，請走 OFFICIAL v18.x patch。



- 說明：由程式自動擷取 `TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18_3_PATCH.md` 的標題與強制詞條款；完成後勾選 [x]。如需調整映射，請走 OFFICIAL v18.x patch。


<!-- AUTO:M8_PATCH_TASKS_END -->\n




<!-- AUTO:PATCH_TASKS_BEGIN -->\n<!-- AUTO_PATCH_TASKS_START -->

## v18.x 補強條款 → 任務清單（自動生成） / Patch-to-Tasks (AUTO)

### v18_1 條款落地任務 / v18_1 Compliance Tasks (AUTO)

- 說明：保守抽取 `TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18_1_PATCH.md` 的關鍵條款（上限 30 條/檔）避免任務爆量；完成後勾選 [x]。

- [ ] [TASK:M8-V18_1-001-7a95b6ce] **B) TAIFEX 在地交易所硬限制：必做的「送單前」驗證（避免 Rejected / 錯單）**
- [ ] [TASK:M8-V18_1-002-ee50c910] **B1) Order Size Limits（最容易踩雷） / B1) Order Size Limits（最容易踩雷）**
- [ ] [TASK:M8-V18_1-003-79f83750] **Market order：日盤每筆最多 10 口；夜盤每筆最多 5 口。 / Market order：日盤每筆最多 10 口；夜盤每筆最多 5 口。**
- [ ] [TASK:M8-V18_1-004-fc980694] **=> v18 的 OrderGuard 必須把 TAIFEX order-size-limit 規則做成「硬擋」：超過就拆單或拒單（依 policy）。 / => v18 的 OrderGuard 必須把 TAIFEX order-size-limit 規則做成「硬擋」：超過就拆單或拒單（依 policy）。**
- [ ] [TASK:M8-V18_1-005-f3030576] **=> 你的滑價/成交概率/拒單風險評估，必須按交易所定義建模；不能只用“理想化市價單”。 / => 你的滑價/成交概率/拒單風險評估，必須按交易所定義建模；不能只用“理想化市價單”。**
- [ ] [TASK:M8-V18_1-006-753b031d] **B3) Price limit / dynamic mechanisms：要把“交易所保護”當成 regime**
- [ ] [TASK:M8-V18_1-007-4824f2bc] **=> v18 的 Regime Engine（或 market regime）必須把「靠近漲跌停/擴大/動態機制觸發」當成禁做或降風險模式，至少做到： / => v18 的 Regime Engine（或 market regime）必須把「靠近漲跌停/擴大/動態機制觸發」當成禁做或降風險模式，至少做到：**
- [ ] [TASK:M8-V18_1-008-f1808f9b] **C) Shioaji / 永豐金：事件真相源的「更嚴格」落地規則**
- [ ] [TASK:M8-V18_1-009-0ecf651d] **C1) Deal 事件可能先於 Order 事件（必須容忍 out-of-order） / C1) Deal 事件可能先於 Order 事件（必須容忍 out-of-order）**
- [ ] [TASK:M8-V18_1-010-b0498bb4] **=> v18 的 Event Sourcing 必須保證： / => v18 的 Event Sourcing 必須保證：**
- [ ] [TASK:M8-V18_1-011-c1914c9c] **不能假設「order event 一定先到」。 / 不能假設「order event 一定先到」。**
- [ ] [TASK:M8-V18_1-012-5037f759] **C2) subscribe_trade 必須視為“可關閉但不建議” / C2) subscribe_trade 必須視為“可關閉但不建議”**
- [ ] [TASK:M8-V18_1-013-544b3c33] **=> v18.1：除非是 research-only sandbox，否則 強制 subscribe_trade=True。 / => v18.1：除非是 research-only sandbox，否則 強制 subscribe_trade=True。**
- [ ] [TASK:M8-V18_1-014-740a564e] **D2) Drift 必須先被量化：Concept drift detector + 失效處置 / D2) Drift 必須先被量化：Concept drift detector + 失效處置**
- [ ] [TASK:M8-V18_1-015-993b41ff] **drift 檢測（統計/模型型）， / drift 檢測（統計/模型型），**
- [ ] [TASK:M8-V18_1-016-f29bc2bf] **drift 觸發後的策略凍結/降級/切換， / drift 觸發後的策略凍結/降級/切換，**
- [ ] [TASK:M8-V18_1-017-ae08cd38] **必須採用 風險約束（如 CVaR/mean-variance constraints）或安全 RL 的 constraint formulation。 / 必須採用 風險約束（如 CVaR/mean-variance constraints）或安全 RL 的 constraint formulation。**
- [ ] [TASK:M8-V18_1-018-88bf2570] **E1) 強制 Blameless Postmortem（但要“可執行改進”） / E1) 強制 Blameless Postmortem（但要“可執行改進”）**
- [ ] [TASK:M8-V18_1-019-068690e6] **[B] TAIFEX OrderGuard（硬擋） / [B] TAIFEX OrderGuard（硬擋）**
- [ ] [TASK:M8-V18_1-020-f80c7aa3] **[C] Shioaji 事件亂序容忍 / [C] Shioaji 事件亂序容忍**
- [ ] [TASK:M8-V18_1-021-06637535] **TAIFEX Order Size Limits、Order Types（MWP） / TAIFEX Order Size Limits、Order Types（MWP）**
- [ ] [TASK:M8-V18_1-022-52d40a2c] **Shioaji Futures order/deal event 文檔（deal event may arrive sooner） / Shioaji Futures order/deal event 文檔（deal event may arrive sooner）**

### v18_2 條款落地任務 / v18_2 Compliance Tasks (AUTO)

- 說明：保守抽取 `TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18_2_PATCH.md` 的關鍵條款（上限 30 條/檔）避免任務爆量；完成後勾選 [x]。

- [ ] [TASK:M8-V18_2-001-6771af16] **TAIFEX 動態價格穩定措施（Dynamic Price Banding Mechanism, DPBM）：當成交模擬價超過上下限，交易所會直接拒單；策略與執行層必須能偵測/處理被拒與重新報價（含撤單/重掛/降價/退避）。citeturn0search0turn0search4turn0search12turn0search16turn0search8 / TAIFEX 動態價格穩定措施（Dynamic Price Banding Mechanism, DPBM）：當成交模擬價超過上下限，交易所會直接拒單；策略與執行層必須能偵測/處理被拒與重新報價（含撤單/重掛/降價/退避）。citeturn0search0turn0search4turn0search12turn0search16turn0search8**
- [ ] [TASK:M8-V18_2-002-3a2fb357] **0.2 執行端（永豐金 Shioaji） / 0.2 執行端（永豐金 Shioaji）**
- [ ] [TASK:M8-V18_2-003-bf491618] **Shioaji 的 Streaming Market Data / subscribe(tick,bidask)、quote callback、以及 quote-binding 等高階用法，必須被納入「報價中斷偵測、延遲監控、撮合保護、與策略節流」。citeturn0search1turn0search21turn0search5turn0search13**
- [ ] [TASK:M8-V18_2-004-f7be1b4f] **1.1 交易型期望值的三層分解（必須在研究報告中固定輸出） / 1.1 交易型期望值的三層分解（必須在研究報告中固定輸出）**
- [ ] [TASK:M8-V18_2-005-1c4a277c] **例：趨勢/動能、均值回歸、breakout、order-flow/微結構訊號、期限結構/日內季節性等。 / 例：趨勢/動能、均值回歸、breakout、order-flow/微結構訊號、期限結構/日內季節性等。**
- [ ] [TASK:M8-V18_2-006-353a0b6f] **任何估計都要報：估計區間、樣本分布、斷點（regime shift）敏感度、與成本/滑價假設。 / 任何估計都要報：估計區間、樣本分布、斷點（regime shift）敏感度、與成本/滑價假設。**
- [ ] [TASK:M8-V18_2-007-2675dec4] **多重檢定控制：參數 sweep 不是越多越好；必須有「白紙假說」與「淘汰率」。使用 purged CV / CPCV 才能把過擬合壓下來。citeturn0search3turn0search19**
- [ ] [TASK:M8-V18_2-008-cd2e8d4b] **2.1 必備的「微結構資料欄位」（若 Shioaji 可得，優先用；不可得則以 proxy） / 2.1 必備的「微結構資料欄位」（若 Shioaji 可得，優先用；不可得則以 proxy）**
- [ ] [TASK:M8-V18_2-009-3a229c66] **mid price、spread（ticks & bps）、order book imbalance（L1~L5）、microprice、trade sign / aggressive side（可用 bidask+last 估）、短窗成交量/筆數、短窗 volatility、短窗撤單率/更新率（若可估）。**
- [ ] [TASK:M8-V18_2-010-1a21fd7e] **成本 = 手續費/稅 + spread crossing + impact + latency drift + rejection re-quote cost / 成本 = 手續費/稅 + spread crossing + impact + latency drift + rejection re-quote cost**
- [ ] [TASK:M8-V18_2-011-0ed3c289] **必須把 DPBM 拒單視為「額外成本風險」，並輸出 rejection 的條件統計。citeturn0search0turn0search12 / 必須把 DPBM 拒單視為「額外成本風險」，並輸出 rejection 的條件統計。citeturn0search0turn0search12**
- [ ] [TASK:M8-V18_2-012-81743694] **波動率目標化（Volatility Targeting）：用波動率當 position sizing 的「共同尺度」，能把不同 regime 的曝險拉回可控範圍。 / 波動率目標化（Volatility Targeting）：用波動率當 position sizing 的「共同尺度」，能把不同 regime 的曝險拉回可控範圍。**
- [ ] [TASK:M8-V18_2-013-a22d9836] **`vol_regime`: 低/中/高（可用 ATR、realized vol、或交易所波動指數 proxy） / `vol_regime`: 低/中/高（可用 ATR、realized vol、或交易所波動指數 proxy）**
- [ ] [TASK:M8-V18_2-014-d5ae1de0] **`signal_confidence` 必須被 `vol_regime` 調制（高波動時假訊號更多、滑價更大） / `signal_confidence` 必須被 `vol_regime` 調制（高波動時假訊號更多、滑價更大）**
- [ ] [TASK:M8-V18_2-015-150f6ba5] **但必須有：vol targeting、drawdown throttle、consecutive loss cooldown、與日內風險重置規則（v18 已有，這裡要求必須與 sizing 綁死） / 但必須有：vol targeting、drawdown throttle、consecutive loss cooldown、與日內風險重置規則（v18 已有，這裡要求必須與 sizing 綁死）**
- [ ] [TASK:M8-V18_2-016-db4c88c6] **Kelly 只能當「上限參考」，不可直接全額套用；必須用 fractional Kelly，並且用保守估計（下分位的勝率/報酬比）做輸入。 / Kelly 只能當「上限參考」，不可直接全額套用；必須用 fractional Kelly，並且用保守估計（下分位的勝率/報酬比）做輸入。**
- [ ] [TASK:M8-V18_2-017-57a31f51] **如果策略是 regime-sensitive（大多數都是），Kelly 估計必須分 regime 做，且要有 shrinkage（向整體均值收縮）。 / 如果策略是 regime-sensitive（大多數都是），Kelly 估計必須分 regime 做，且要有 shrinkage（向整體均值收縮）。**
- [ ] [TASK:M8-V18_2-018-53e6b437] **`ORDER_REJECTED_DPBM`： / `ORDER_REJECTED_DPBM`：**
- [ ] [TASK:M8-V18_2-019-3377083f] **5.2 Shioaji 串流與斷線治理（必做） / 5.2 Shioaji 串流與斷線治理（必做）**
- [ ] [TASK:M8-V18_2-020-d8777cb9] **max order size、max position、max notional、max order rate、max message rate、price band sanity check、self-trade prevention（若平台支援）、kill switch。citeturn0search10turn0search6turn0search14 / max order size、max position、max notional、max order rate、max message rate、price band sanity check、self-trade prevention（若平台支援）、kill switch。citeturn0search10turn0search6turn0search14**
- [ ] [TASK:M8-V18_2-021-420add21] **6.1 最小可行的自我改進（v18 主線必須內建） / 6.1 最小可行的自我改進（v18 主線必須內建）**
- [ ] [TASK:M8-V18_2-022-bf1ad4a1] **任何「自動調參」都必須在 paper 環境先跑過 purged CV + walk-forward，再進 canary。citeturn0search3turn0search15 / 任何「自動調參」都必須在 paper 環境先跑過 purged CV + walk-forward，再進 canary。citeturn0search3turn0search15**

### v18_3 條款落地任務 / v18_3 Compliance Tasks (AUTO)

- 說明：保守抽取 `TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18_3_PATCH.md` 的關鍵條款（上限 30 條/檔）避免任務爆量；完成後勾選 [x]。

- [ ] [TASK:M8-V18_3-001-a7fe2fe4] **1) Execution Safety：交易所硬限制（TAIFEX）送單前必做 Preflight（不可繞過） / 1) Execution Safety：交易所硬限制（TAIFEX）送單前必做 Preflight（不可繞過）**
- [ ] [TASK:M8-V18_3-002-440781b3] **若策略/執行要求 qty > limit：必須拆單（SPLIT） 或 REJECT；不得硬送導致交易所拒單（Rejected）造成不可控成本與狀態漂移。 / 若策略/執行要求 qty > limit：必須拆單（SPLIT） 或 REJECT；不得硬送導致交易所拒單（Rejected）造成不可控成本與狀態漂移。**
- [ ] [TASK:M8-V18_3-003-1d0b5bd3] **1.2 MWP（Market with Protection）必須使用「交易所定義」的轉限價邏輯 / 1.2 MWP（Market with Protection）必須使用「交易所定義」的轉限價邏輯**
- [ ] [TASK:M8-V18_3-004-22015bfd] **因此執行層在產生/驗證 MWP 時，必須具備： / 因此執行層在產生/驗證 MWP 時，必須具備：**
- [ ] [TASK:M8-V18_3-005-e57a34a4] **該 gate 必須在「實際送到 broker/OMS」之前發生（pre-trade）。 / 該 gate 必須在「實際送到 broker/OMS」之前發生（pre-trade）。**
- [ ] [TASK:M8-V18_3-006-c179107b] **3) SPLIT 證據鏈：必須寫入 Parent Row + Children Row（可回放/可對帳） / 3) SPLIT 證據鏈：必須寫入 Parent Row + Children Row（可回放/可對帳）**
- [ ] [TASK:M8-V18_3-007-bfd45174] **3.1 必須落庫的最小證據 / 3.1 必須落庫的最小證據**
- [ ] [TASK:M8-V18_3-008-1e89b96d] **`broker_order_id = split_parent_id` / `broker_order_id = split_parent_id`**
- [ ] [TASK:M8-V18_3-009-15ebf7ec] **meta 必須包含：`split_parent_id`, `split_index` / meta 必須包含：`split_parent_id`, `split_index`**
- [ ] [TASK:M8-V18_3-010-18341565] **但 audit 必須有「可觀測」的失敗訊號（例如 ops log / diag counter）— 後續 M8/M9 再落地。**
- [ ] [TASK:M8-V18_3-011-a1a8880b] **Wrapper 呼叫 `risk.check_pre_trade(...)` 時，必須允許： / Wrapper 呼叫 `risk.check_pre_trade(...)` 時，必須允許：**
- [ ] [TASK:M8-V18_3-012-2c9fc132] **execution/taifex_preflight_v1.py：effective price type + market qty limit + MWP validation / execution/taifex_preflight_v1.py：effective price type + market qty limit + MWP validation**

<!-- AUTO_PATCH_TASKS_END -->\n<!-- AUTO:PATCH_TASKS_END -->



