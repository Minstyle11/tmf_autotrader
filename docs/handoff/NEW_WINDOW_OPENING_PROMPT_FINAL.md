# TMF AutoTrader — NEW WINDOW OPENING PROMPT (ULTRA / OFFICIAL-LOCKED / v18 One-Truth)
- 生成時間：2026-02-02T22:25:13+08:00

## 0) One-Truth / One-Doc / One-OS（絕對規則）
- 唯一真相源：`docs/bibles/TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18.md`（只允許 v18.x patch）。
- 任何與 v18 衝突者，一律以 v18 為準。
- 事件真相源：只認 DB 落盤 events（呼叫成功不算成立）。

### v18 sha256（驗收必做）
```
662310df2d4f916ca826b041e5bc703ad3c8622922e3aec757931e80285e4f99  TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18.md
```
- v18 檔案存在：True

## 1) 新視窗第一輪必做（Hard Gate / 不可跳）
```bash
cd ~/tmf_autotrader

# 1) v18 sha256 verify (ONE-TRUTH)
sha256sum docs/bibles/TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18.md | tee /tmp/v18.sha256
cat docs/bibles/TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18.md.sha256.txt

# 2) latest ULTRA windowpack sha256 verify (if you are using zip handoff)
sha256sum runtime/handoff/latest/TMF_AutoTrader_WindowPack_ULTRA_20260202_211348.zip | tee /tmp/latest_pack.sha256
cat runtime/handoff/latest/TMF_AutoTrader_WindowPack_ULTRA_20260202_211348.zip.sha256.txt

# 3) Read audit + next_step (then execute next_step as a bash script if it is executable-style)
sed -n '1,200p' runtime/handoff/state/audit_report_latest.md
sed -n '1,200p' runtime/handoff/state/next_step.txt
```

## 2) 最新 ULTRA WindowPack（接手用）
- latest_zip: `runtime/handoff/latest/TMF_AutoTrader_WindowPack_ULTRA_20260202_211348.zip`
```
200516888efb1cd1d3753d5a1edaf9234e10c99e9f27e6cdcc88e43962f71115  TMF_AutoTrader_WindowPack_ULTRA_20260202_211348.zip
```

## 3) PROJECT_BOARD（摘錄）
```
# 專案進度總覽（自動計算）
- 更新時間：2026-02-02 22:21:46
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
```

## 4) latest_state.json（原文）
```json
{
  "ts": "2026-02-02T16:56:53",
  "board_total_pct": "63.6",
  "launchd": {
    "pm_tick": "0",
    "autorestart": "0",
    "backup": "11",
    "handoff_tick": ""
  },
  "last_changelog_line": "- [2026-02-02 16:53:11] pm_tick",
  "paths": {
    "repo": "/Users/williamhsu/tmf_autotrader",
    "handoff_log": "docs/handoff/HANDOFF_LOG.md",
    "opening_prompt_draft": "docs/handoff/NEW_WINDOW_OPENING_PROMPT_DRAFT.md",
    "next_step": "runtime/handoff/state/next_step.txt"
  }
}
```

## 5) audit_report_latest.md（尾段）
```
repo/scripts/ops_audit_hardgate_v1.sh.bak.grepfix_20260130_134838: OK
repo/scripts/ops_env_rebuild_hardgate_v1.sh: OK
repo/scripts/ops_new_window_oneshot_hardgate_v1.sh: OK
repo/scripts/ops_new_window_oneshot_hardgate_v1.sh.bak.fix_sha_sidecar_20260201_223330: OK
repo/scripts/paper_live_integration_smoke_v1.sh: OK
repo/scripts/paper_live_integration_smoke_v1.sh.bak.20260202_132028: OK
repo/scripts/paper_live_integration_smoke_v1.sh.bak.fix_rejected_sql_20260201_230050: OK
repo/scripts/paper_live_integration_smoke_v1.sh.bak.skip_synth_20260202_093149: OK
repo/scripts/patch_recorder_use_groupkey.sh: OK
repo/scripts/patch_shioaji_login_token.sh: OK
repo/scripts/pm_refresh_board.sh: OK
repo/scripts/pm_tick.sh: OK
repo/scripts/repo_root_hygiene_backtick_quarantine_v1.sh: OK
repo/scripts/run_recorder.sh: OK
repo/scripts/set_next_step_v1.sh: OK
repo/scripts/setup_git_hooks_v1.sh: OK
repo/scripts/setup_m0_recorder.sh: OK
repo/src/broker/shioaji_recorder.py: OK
repo/src/cost/cost_model_v1.py: OK
repo/src/data/build_bars_1m_v1.py: OK
repo/src/data/normalize_events_v1.py: OK
repo/src/data/store_sqlite_v1.py: OK
repo/src/market/market_metrics_from_db_v1.py: OK
repo/src/oms/__init__.py: OK
repo/src/oms/demo_paper_oms_v1.py: OK
repo/src/oms/models_v1.py: OK
repo/src/oms/paper_oms_risk_safety_wrapper_v1.py: OK
repo/src/oms/paper_oms_risk_safety_wrapper_v1.py.bak.audit_persist_20260201_225625: OK
repo/src/oms/paper_oms_risk_wrapper_v1.py: OK
repo/src/oms/paper_oms_v1.py: OK
repo/src/oms/paper_oms_v1.py.bak.merge_meta_20260130_235458: OK
repo/src/oms/paper_oms_v1.py.bak.place_order_20260129: OK
repo/src/oms/run_paper_live_v1.py: OK
repo/src/oms/run_paper_live_v1.py.bak.20260202_132028: OK
repo/src/oms/run_paper_live_v1.py.bak.fix_if_indent_20260201_224828: OK
repo/src/oms/run_paper_live_v1.py.bak.fix_indent_20260201_224735: OK
repo/src/oms/run_paper_live_v1.py.bak.market_metrics_truth_20260201_224453: OK
repo/src/oms/run_paper_live_v1.py.bak.reindent_market_metrics_dict_20260201_224946: OK
repo/src/risk/demo_risk_market_quality_v1.py: OK
repo/src/risk/demo_risk_pretrade_v1.py: OK
repo/src/risk/demo_risk_pretrade_v1.py.bak.20260130_000308: OK
repo/src/risk/demo_risk_pretrade_v1.py.bak.demo_fix_20260129: OK
repo/src/risk/demo_risk_pretrade_v1.py.bak.fix_top_level_indent_20260130_001806: OK
repo/src/risk/demo_risk_pretrade_v1.py.bak.fix_unmatched_paren_20260130_001658: OK
repo/src/risk/demo_risk_pretrade_v1.py.bak.rebuild_dbproof_20260130_002304: OK
repo/src/risk/in_trade_controls_v1.py: OK
repo/src/risk/risk_engine_v1.py: OK
repo/src/risk/risk_engine_v1.py.bak.fix_stopmsg_20260130_080846: OK
repo/src/risk/run_risk_gates_smoke_v1.py: OK
repo/src/safety/system_safety_v1.py: OK
repo/src/sim/sim_one_trade_v1.py: OK
repo/src/sim/slippage_model_v1.py: OK
state/NEW_WINDOW_CLIPBOARD_ULTRA_ZH.txt: OK
state/NEW_WINDOW_CLIPBOARD_ULTRA_ZH.txt.sha256.txt: OK
state/NEW_WINDOW_ONESHOT_HARDGATE_SOP.txt: OK
state/audit_report_latest.md: OK
state/env_rebuild_report_latest.md: OK
state/latest_state.json: OK
state/next_step.txt: OK
```
- OK
## 8) M2 regression smoke (risk gates)
```
[CASE A] daily max loss -> REJECT RISK_DAILY_MAX_LOSS
[CASE B] consec losses cooldown -> REJECT RISK_CONSEC_LOSS_COOLDOWN
[CASE C] cooldown expired -> PASS OK
[OK] m2 regression risk gates PASS (temp db): /var/folders/k7/6dt2zlt50bdb9m31cb3w10vr0000gn/T/tmp.H43klFngmZ/tmf_autotrader_v1_regtest.sqlite3
[OK] wrote log: runtime/logs/m2_regression_risk_gates_v1.last.log
```
- OK

## RESULT
- PASS

## [HARD-REQ] Opening Prompt in Latest ULTRA ZIP
- zip: `runtime/handoff/latest/TMF_AutoTrader_WindowPack_ULTRA_20260202_210302.zip`
- required files:
  - `runtime/handoff/state/NEW_WINDOW_OPENING_PROMPT_ULTRA_ZH.md`
  - `runtime/handoff/state/NEW_WINDOW_OPENING_PROMPT_ULTRA_ZH.md.sha256.txt`
- check: unzip list contains opening prompt ✔
```

## 6) next_step.txt（原文）
```
#!/bin/bash
set -euo pipefail
cd "$HOME/tmf_autotrader"

# NEXT (M2 Pre-trade gates -> productionize):
# Goal:
#  1) Add a real MarketMetrics source (bid/ask/spread/ATR/liquidity) for paper-live (not manual meta).
#  2) Optionally flip strict_require_market_metrics=1 in paper-live runner only (keep demos unchanged).
#  3) Prove with: m2_regression_risk_gates_v1.sh + m2_regression_market_quality_gates_v1.sh + paper_live_integration_smoke_v1.sh

# Step 1: inspect where paper-live currently builds meta, and where we can inject market_metrics safely
python3 - <<'PY2'
from pathlib import Path

p = Path("src/oms/run_paper_live_v1.py")
print("exists=", p.exists())
if p.exists():
    txt = p.read_text(encoding="utf-8", errors="replace")
    print(txt[:1600])
PY2

echo "=== [TODO] Implement MarketMetricsProviderV1 + wire into run_paper_live_v1.py meta.market_metrics ==="
```

## 7) CHANGELOG（尾段）
```
(missing CHANGELOG.md)
```

## 8) HANDOFF_LOG（尾段）
```
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
```

### Changelog (tail)

```text
- [2026-02-02 20:03:18] pm_tick
- [2026-02-02 20:08:18] pm_tick
- [2026-02-02 20:13:18] pm_tick
- [2026-02-02 20:18:18] pm_tick
- [2026-02-02 20:23:18] pm_tick
- [2026-02-02 20:28:19] pm_tick
- [2026-02-02 20:33:19] pm_tick
- [2026-02-02 20:38:19] pm_tick
- [2026-02-02 20:43:19] pm_tick
- [2026-02-02 20:48:19] pm_tick
- [2026-02-02 20:53:20] pm_tick
- [2026-02-02 20:58:20] pm_tick
- [2026-02-02 21:03:20] pm_tick
- [2026-02-02 21:08:20] pm_tick
- [2026-02-02 21:13:20] pm_tick
```

### Working tree (git status --porcelain)

```text
 M docs/board/CHANGELOG.md
 M docs/board/PROJECT_BOARD.md
 M docs/handoff/HANDOFF_LOG.md
 M docs/handoff/NEW_WINDOW_OPENING_PROMPT_DRAFT.md
 M docs/handoff/NEW_WINDOW_OPENING_PROMPT_FINAL.md
?? docs/ops/TMF_WEBSEARCH_RULE_BIBLE_v1.md
```

### Next terminal step (head)

```text
#!/bin/bash
set -euo pipefail
cd "$HOME/tmf_autotrader"

# NEXT (M2 Pre-trade gates -> productionize):
# Goal:
#  1) Add a real MarketMetrics source (bid/ask/spread/ATR/liquidity) for paper-live (not manual meta).
#  2) Optionally flip strict_require_market_metrics=1 in paper-live runner only (keep demos unchanged).
#  3) Prove with: m2_regression_risk_gates_v1.sh + m2_regression_market_quality_gates_v1.sh + paper_live_integration_smoke_v1.sh

# Step 1: inspect where paper-live currently builds meta, and where we can inject market_metrics safely
python3 - <<'PY2'
```
```

## 9) 互動協議（強制）
- 每回合只跑一個 Terminal 指令；貼回輸出後才進下一步。
- 任何卡住（bquote>/cmdand/等待無輸出）不要叫使用者 Ctrl+C；直接給下一個新指令。
- 一切以 v18 為準（One-Truth）。

