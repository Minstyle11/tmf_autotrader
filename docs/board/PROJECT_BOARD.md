# 專案進度總覽（自動計算）
- 更新時間：2026-02-02 19:28:16
- 專案總完成度：63.6% （已完成 14 / 22 項）

## 里程碑完成度
- M0 Foundations：100.0% （已完成 4 / 4）
- M1 Sim + Cost Model：100.0% （已完成 3 / 3）
- M2 Risk Engine v1 (Risk First)：100.0% （已完成 3 / 3）
- M3 Strategy Base + Paper Live：42.9% （已完成 3 / 7）

## 說明（快速讀法）
- 看「專案總完成度」掌握全局；看「里程碑完成度」掌握目前在哪一段。
- [~] 進行中、[!] 阻塞、[x] 已完成。

# TMF AutoTrader Project Board (OFFICIAL)

## Status Legend
- [ ] TODO
- [~] DOING
- [x] DONE
- [!] BLOCKED

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
- [x] Pre-trade gates (DONE: stop-required + per-trade max loss + daily max loss + consecutive-loss cooldown + market-quality gates (spread/ATR/liquidity) + regressions; TODO: wire real market_metrics source + decide strict_require_market_metrics for paper-live)
- [x] In-trade controls (SL/TS/breakeven, time-stop, session-aware rules)
- [x] System safety (disconnect handling, session state machine, expiry-day guards)

### M3 Strategy Base + Paper Live
- [ ] Trend strategy v1 (dual-side) + attribution logging
- [ ] Mean-reversion v1 (dual-side) + attribution logging
- [ ] Daily report v1 + auto diagnostics

## Always-On Bibles (must obey)
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
- [ ] Wire decision into PaperOMSRiskSafetyWrapperV1 / live runner (next)
