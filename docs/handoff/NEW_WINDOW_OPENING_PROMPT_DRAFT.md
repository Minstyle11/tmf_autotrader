# NEW WINDOW OPENING PROMPT (FINAL, AUTO-UPDATED)

## Current status (Board head)

```text
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

- 更新時間：2026-02-21 10:37:13
- 專案總完成度：30.0% （已完成 24 / 80 項；TODO 56 / DOING 0 / BLOCKED 0）

<!-- AUTO:PROGRESS_BEGIN -->
- **TOTAL:** 80
- **TODO:** 56
- **DOING:** 0
- **DONE:** 24
- **BLOCKED:** 0
- **PCT:** 30.0%
- **LAST_BOARD_UPDATE_AT:** 2026-02-21 10:37:13
<!-- AUTO:PROGRESS_END -->
## 里程碑完成度
- M0 Foundations：100.0% （已完成 4 / 4）
- M1 Sim + Cost Model：100.0% （已完成 3 / 3）
- M2 Risk Engine v1 (Risk First)：100.0% （已完成 3 / 3）
- M3 Strategy Base + Paper Live：42.9% （已完成 3 / 7）

## 說明（快速讀法）
- 進行中、[!] 阻塞、[x] 已完成。

# TMF AutoTrader Project Board (OFFICIAL)
```

## Latest changes (Changelog tail)

```text
- [2026-02-04 20:05:24] pm_tick
- [2026-02-04 20:10:25] pm_tick
- [2026-02-04 20:15:25] pm_tick
- [2026-02-04 20:18:36] test_tick_no_board_touch
- [2026-02-04 20:20:25] pm_tick
- [2026-02-04 20:25:26] pm_tick
- [2026-02-04 20:30:26] pm_tick
- [2026-02-04 20:33:20] pm_refresh_board
- [2026-02-04 20:35:26] pm_tick
- [2026-02-04 20:40:27] pm_tick
- [2026-02-04 20:45:27] pm_tick
- [2026-02-04 20:50:28] pm_tick
- [2026-02-10 15:17:35] Auto-verify PROJECT_BOARD + handoff artifacts
- [2026-02-10 17:08:53] Auto: verify PROJECT_BOARD after independent autoprog patch
- [2026-02-10 23:31:08] M3: LIVE snapshot OK (non-synth/non-ops_seed bidask+tick; SystemSafetyEngineV1 OK; market_metrics non-empty) + PROJECT_BOARD autoprog reconciled (25/107=23.4%)
```

## Working tree (git status --porcelain)

```text
 M .githooks/pre-commit
 M .githooks/pre-push
A  .github/workflows/board_gate.yml
 M .pre-commit-config.yaml
 M docs/bibles/TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18.md.sha256.txt
 M docs/board/PROJECT_BOARD.md
 M docs/handoff/HANDOFF_LOG.md
 M docs/handoff/NEW_WINDOW_OPENING_PROMPT_DRAFT.md
 M docs/handoff/NEW_WINDOW_OPENING_PROMPT_FINAL.md
 M docs/ops/OPS_INDEX.md
 M execution/order_guard.py
 M execution/taifex_preflight_v1.py
 M ops/drills/drill_runner.py
 M risk/options/stress_battery.py
 M runtime/handoff/state/latest_state.json
 M scripts/board_canonical_counts_v1.py
 M scripts/gen_new_window_opening_prompt_ultra_zh.py
 M scripts/m3_regression_cost_model_os_v1.sh
 M scripts/m3_regression_paper_live_smoke_v1.sh
 M scripts/m3_regression_suite_v1.sh
 M scripts/m8_update_board_from_patches_v1.py
 M scripts/mk_windowpack_ultra.sh
 M scripts/ops_audit_hardgate_v1.sh
 M scripts/pm_refresh_board_and_verify.sh
 M scripts/run_paper_live_smoke_suite_v1.py
 M snapshots/spec_diff/spec_diff_report_diff.md
 M snapshots/spec_diff/spec_diff_report_latest.md
 M src/cost/cost_model_v1.py
 M src/data/store_sqlite_v1.py
 M src/oms/paper_oms_risk_safety_wrapper_v1.py
 M src/oms/paper_oms_v1.py
 M src/ops/latency/backpressure_governor.py
 M src/safety/system_safety_v1.py
 M src/sim/run_strategies_paper_loop_v1.py
 M src/sim/run_strategies_paper_v1.py
?? docs/ops/DAILY_FINANCE_CLOSE_PACK_OFFICIAL_SNAPSHOT_20260220_161001.md
?? docs/ops/DAILY_FINANCE_CLOSE_PACK_OFFICIAL_SNAPSHOT_20260220_161001.md.sha256.txt
?? docs/ops/PROJECT_BOARD_ULTRA_GOVERNANCE_BIBLE_v1.md
?? docs/ops/PROJECT_BOARD_ULTRA_GOVERNANCE_BIBLE_v1.md.sha256.txt
?? docs/ops/PROJECT_BOARD_ULTRA_GOVERNANCE_BIBLE_v1_1_PATCH.md
?? docs/ops/PROJECT_BOARD_ULTRA_GOVERNANCE_BIBLE_v1_1_PATCH.md.sha256.txt
?? docs/ops/PROJECT_BOARD_ULTRA_GOVERNANCE_BIBLE_v1_2_PATCH.md
?? docs/ops/PROJECT_BOARD_ULTRA_GOVERNANCE_BIBLE_v1_2_PATCH.md.sha256.txt
?? docs/ops/PROJECT_BOARD_ULTRA_GOVERNANCE_BIBLE_v1_3_PATCH.md
?? docs/ops/PROJECT_BOARD_ULTRA_GOVERNANCE_BIBLE_v1_3_PATCH.md.sha256.txt
?? e
?? scripts/board_ultra_hardgate_v1.py
?? scripts/fix_indent_and_patch_m3_os_latbp_v1.py
?? scripts/m3_regression_latency_backpressure_v1.sh
?? scripts/m3_regression_stress_battery_os_v1.sh
?? scripts/ops_board_ultra_repair_v1.py
?? scripts/ops_chaos_drill_v1.sh
?? scripts/ops_runbook_drill_v1.sh
?? scripts/patch_m3_os_latbp_inject_v2.py
?? scripts/patch_m3_os_latency_backpressure_v1.py
?? src/ops/chaos/
```

## Next terminal step (runtime/handoff/state/next_step.txt)

```text
# NEXT STEP (portable, UNPACK_ROOT-agnostic; PACK_ROOT-aware)
UNPACK_ROOT="${UNPACK_ROOT:-$(ls -dt /tmp/tmf_autotrader_newwindow_unpack_* 2>/dev/null | head -1)}"
if [ -z "$UNPACK_ROOT" ] || [ ! -d "$UNPACK_ROOT" ]; then
  echo "[FATAL] cannot locate UNPACK_ROOT. Expected /tmp/tmf_autotrader_newwindow_unpack_*"
  echo "Hint: re-run OneShot HardGate to regenerate an unpack, or export UNPACK_ROOT to the correct path."
  exit 2
fi

# Pack root is the first directory under UNPACK_ROOT (e.g. tmf_autotrader_windowpack_ultra_YYYYMMDD_HHMMSS)
PACK_ROOT="${PACK_ROOT:-$(find "$UNPACK_ROOT" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | head -n 1)}"
if [ -z "$PACK_ROOT" ] || [ ! -d "$PACK_ROOT/repo" ]; then
  echo "[FATAL] cannot locate PACK_ROOT/repo under UNPACK_ROOT=$UNPACK_ROOT"
  echo "Hint: set PACK_ROOT to the tmf_autotrader_windowpack_ultra_* dir under UNPACK_ROOT."
  exit 2
fi

cd "$PACK_ROOT/repo" && sed -n "1,220p" runtime/handoff/state/NEW_WINDOW_OPENING_PROMPT_ULTRA_ZH.md
```

## Rules (must follow)
- One terminal command per turn.
- Append-only logs; no silent rewrites.
- One-click ZIP only when assistant signals capacity risk.
