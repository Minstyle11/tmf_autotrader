# NEW WINDOW OPENING PROMPT (FINAL, AUTO-UPDATED)

## Current status (Board head)

```text
# 專案進度總覽（自動計算）

<!-- AUTO_PROGRESS_START -->
**專案總完成度 / Overall completion:** 28.0%（已完成 30 / 107 項；未完成 77 項）

- done   : 20
- doing  : 0
- blocked: 0
- todo   : 77
- invalid_like: 0
<!-- AUTO_PROGRESS_END -->
**專案總完成度 / Overall completion:** 28.0%（已完成 30 / 107 項；未完成 77 項）

- 更新時間：2026-02-20 01:52:00
- 專案總完成度：28.0% （已完成 30 / 107 項；TODO 77 / DOING 0 / BLOCKED 0）

<!-- AUTO:PROGRESS_BEGIN -->
- **TOTAL:** 107
- **TODO:** 77
- **DOING:** 0
- **DONE:** 30
- **BLOCKED:** 0
- **PCT:** 28.0%
- **LAST_BOARD_UPDATE_AT:** 2026-02-20 01:52:00
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
AM .editorconfig
AM .gitattributes
M  .githooks/pre-commit
M  .githooks/pre-push
A  .github/workflows/precommit.yml
M  .gitignore
AM .pre-commit-config.yaml
M  MANIFEST_SHA256_ALL_FILES.txt
M  broker/shioaji_adapter.py
M  broker/shioaji_callbacks.py
M  broker/shioaji_preflight.py
M  "docs/_inbox/tmf_autotrader\345\260\210\346\241\210 - \346\206\262\346\263\225\347\264\232\350\246\217\347\257\204.rtf"
M  docs/bibles/02_OPS_HARDGATE_PACK_BIBLE_v1.md
M  docs/bibles/HANDOFF_SOP_OFFICIAL_BIBLE_v1.md
A  docs/bibles/PROJECT_BOARD_AUTOSYNC_CONSTITUTION_BIBLE_v1.md
A  docs/bibles/PROJECT_BOARD_AUTOSYNC_CONSTITUTION_BIBLE_v1.md.sha256.txt
A  docs/bibles/PROJECT_BOARD_AUTO_PROGRESS_BIBLE_v1.md
A  docs/bibles/PROJECT_BOARD_AUTO_PROGRESS_BIBLE_v1.md.sha256.txt
A  docs/bibles/TMF_AUTOTRADER_CONSTITUTION_RULES_v1.rtf
A  docs/bibles/TMF_AUTOTRADER_CONSTITUTION_RULES_v1.rtf.sha256.txt
M  docs/bibles/TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18.md
M  docs/bibles/TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18_1_PATCH.md
M  docs/bibles/TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18_2_PATCH.md
A  docs/bibles/TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18_3_PATCH.md
A  docs/bibles/TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18_3_PATCH.md.sha256.txt
M  docs/bibles/patches/TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18_1_PATCH.md
M  docs/bibles/patches/TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18_2_PATCH.md
M  docs/board/BIBLES_INDEX_v18x.json
M  docs/board/CHANGELOG.md
MM docs/board/PROJECT_BOARD.md
A  docs/board/PROJECT_BOARD.md.sha256.txt
M  docs/board/REPO_ROOT_HYGIENE_REPORT_20260201_234927.json
M  docs/board/REPO_ROOT_HYGIENE_REPORT_20260201_234927.md
M  docs/board/V18_ALIGN_SWEEP_REPORT_20260201_203308.json
MM docs/handoff/HANDOFF_LOG.md
MM docs/handoff/NEW_WINDOW_OPENING_PROMPT_DRAFT.md
MM docs/handoff/NEW_WINDOW_OPENING_PROMPT_FINAL.md
A  docs/ops/DAILY_FINANCE_CLOSE_PACK_OFFICIAL_SNAPSHOT_20260210_161003.md
A  docs/ops/DAILY_FINANCE_CLOSE_PACK_OFFICIAL_SNAPSHOT_20260210_161003.md.sha256.txt
A  docs/ops/DAILY_FINANCE_CLOSE_PACK_OFFICIAL_SNAPSHOT_20260211_193915.md
A  docs/ops/DAILY_FINANCE_CLOSE_PACK_OFFICIAL_SNAPSHOT_20260211_193915.md.sha256.txt
A  docs/ops/DAILY_FINANCE_CLOSE_PACK_OFFICIAL_SNAPSHOT_20260212_161004.md
A  docs/ops/DAILY_FINANCE_CLOSE_PACK_OFFICIAL_SNAPSHOT_20260212_161004.md.sha256.txt
A  docs/ops/DAILY_FINANCE_CLOSE_PACK_OFFICIAL_SNAPSHOT_20260212_172850.md
A  docs/ops/DAILY_FINANCE_CLOSE_PACK_OFFICIAL_SNAPSHOT_20260212_172850.md.sha256.txt
A  docs/ops/DAILY_FINANCE_CLOSE_PACK_OFFICIAL_SNAPSHOT_20260212_173159.md
A  docs/ops/DAILY_FINANCE_CLOSE_PACK_OFFICIAL_SNAPSHOT_20260212_173159.md.sha256.txt
A  docs/ops/DAILY_FINANCE_CLOSE_PACK_OFFICIAL_SNAPSHOT_20260213_161001.md
A  docs/ops/DAILY_FINANCE_CLOSE_PACK_OFFICIAL_SNAPSHOT_20260213_161001.md.sha256.txt
A  docs/ops/DAILY_FINANCE_CLOSE_PACK_OFFICIAL_SNAPSHOT_20260214_161532.md
A  docs/ops/DAILY_FINANCE_CLOSE_PACK_OFFICIAL_SNAPSHOT_20260214_161532.md.sha256.txt
A  docs/ops/DAILY_FINANCE_CLOSE_PACK_OFFICIAL_SNAPSHOT_20260215_161005.md
A  docs/ops/DAILY_FINANCE_CLOSE_PACK_OFFICIAL_SNAPSHOT_20260215_161005.md.sha256.txt
A  docs/ops/DAILY_FINANCE_CLOSE_PACK_OFFICIAL_SNAPSHOT_20260216_161004.md
A  docs/ops/DAILY_FINANCE_CLOSE_PACK_OFFICIAL_SNAPSHOT_20260216_161004.md.sha256.txt
A  docs/ops/DAILY_FINANCE_CLOSE_PACK_OFFICIAL_SNAPSHOT_20260217_161003.md
A  docs/ops/DAILY_FINANCE_CLOSE_PACK_OFFICIAL_SNAPSHOT_20260217_161003.md.sha256.txt
A  docs/ops/DAILY_FINANCE_CLOSE_PACK_OFFICIAL_SNAPSHOT_20260218_161007.md
A  docs/ops/DAILY_FINANCE_CLOSE_PACK_OFFICIAL_SNAPSHOT_20260218_161007.md.sha256.txt
A  docs/ops/DAILY_FINANCE_CLOSE_PACK_OFFICIAL_SNAPSHOT_20260219_161005.md
A  docs/ops/DAILY_FINANCE_CLOSE_PACK_OFFICIAL_SNAPSHOT_20260219_161005.md.sha256.txt
M  docs/ops/FOP_KEEPFRESH_GUARD_ACCEPTANCE_2026-02-09.md
M  docs/ops/HEALTH_CHECKS_KIND_AND_SMOKE_SUITE_BIBLE_v1.md
M  docs/ops/LAUNCHAGENT_ZSH_ENTRYPOINT_HAZARDS_BIBLE_v1.md
AM docs/ops/LEARNING_GOVERNANCE_V1.md
M  docs/ops/OPS_INDEX.md
M  docs/ops/OPS_INDEX_OFFICIAL_SNAPSHOT_20260204_114806.md
M  docs/ops/OPS_SNAPSHOT_INDEXING_BIBLE_v1.md
M  docs/ops/PM_TICK_LOGROTATE_OFFICIAL_SNAPSHOT_20260204_110006.md
M  docs/ops/PM_TICK_LOGROTATE_RUNLOG_OFFICIAL_SNAPSHOT_20260204_112536.md
A  docs/ops/PROJECT_BOARD_AUTOSYNC_BIBLE_v1.md
A  docs/ops/PROJECT_BOARD_AUTOSYNC_BIBLE_v1.md.sha256.txt
M  docs/ops/PROJECT_BOARD_GOVERNANCE_BIBLE_v1.md
M  docs/ops/RISK_GATES_AUDIT_BIBLE_v1.md
A  docs/ops/TAIFEX_MWP_BIBLE_v1.md
A  docs/ops/TAIFEX_MWP_BIBLE_v1.md.sha256.txt
M  docs/ops/ULTRA_ZERO_GAP_HANDOFF_BIBLE_v1.md
M  docs/runbooks/OPS_RUNBOOK_v1.md
M  execution/reject_policy.yaml
M  execution/reject_taxonomy.py
M  execution/taifex_preflight_v1.py
A  execution/tw_market_calendar_v1.py
A  execution/tw_market_holidays_2026.json
M  ops/reconcile/reconcile_engine.py
A  ops/rejects/reject_stats_from_events_v1.py
M  ops/replay/replay_runner.py
M  ops/run_shioaji_api_test_report.py
M  ops/run_shioaji_stream_healthcheck.py
 M repo/docs/bibles/HANDOFF_SOP_OFFICIAL_BIBLE_v1.md
 M repo/docs/runbooks/HANDOFF_SOP_OFFICIAL_v2.md
 M runtime/handoff/state/latest_state.json
M  scripts/_setup_backup_and_pm.sh
A  scripts/analyze_stop_required_v1.py
A  scripts/board_canonical_counts_v1.py
A  scripts/board_count_m6_status_outside_canonical_v1.py
A  scripts/board_invalid_like_fixlist_v2.py
A  scripts/board_progress_from_block_v1.py
A  scripts/board_rebuild_header_from_task_truth_v1.py
A  scripts/board_sync_header_to_canonical_v1.py
A  scripts/board_sync_v1.py
A  scripts/board_sync_v2.py
A  scripts/board_task_audit_v1.py
A  scripts/build_daily_report_v1.py
A  scripts/build_rejection_stats_v1.py
M  scripts/fop_keepfresh_guard.sh
M  scripts/gen_new_window_opening_prompt_ultra_zh.py
M  scripts/handoff_tick.sh
A  scripts/hooks/board_guard_precommit.sh
M  scripts/inspect_contracts_ready_and_find_txf_family.py
M  scripts/inspect_futures_contracts.py
M  scripts/inspect_index_futures_group_keys.py
M  scripts/m0_fix_jsonl_newline_and_smoke.sh
M  scripts/m0_ops_autorestart_v1.sh
M  scripts/m0_patch_recorder_payload_serialize_v2.sh
M  scripts/m0_patch_recorder_sessionstart_and_smoke.sh
M  scripts/m0_verify_recorder_and_update_board.sh
M  scripts/m3_mainline_runner_v1.sh
M  scripts/m3_regression_audit_replay_os_v1.sh
A  scripts/m3_regression_cost_model_os_v1.sh
A  scripts/m3_regression_healthchecks_smoke_summary_v1.sh
A  scripts/m3_regression_offsession_allow_stale_v1.sh
M  scripts/m3_regression_paper_live_smoke_combo_v1.sh
A  scripts/m3_regression_reject_stats_v1.sh
M  scripts/m3_regression_taifex_split_v1.sh
A  scripts/m6_count_overall_outside_canonical_v1.py
A  scripts/m8_regression_taifex_orderguard_v1.sh
A  scripts/m8_regression_taifex_orderguard_v1_post.sh
M  scripts/m8_update_board_from_patches_v1.py
M  scripts/mk_windowpack_ultra.sh
A  scripts/oneshot_hardgate_verify_windowpack_ultra_v1.py
M  scripts/ops_audit_hardgate_v1.sh
M  scripts/ops_env_rebuild_hardgate_v1.sh
A  scripts/ops_live_snapshot_v1.py
A  scripts/ops_mark_board_tasks_done_v1.py
A  scripts/ops_market_calendar_status_v1.py
M  scripts/ops_new_window_oneshot_hardgate_v1.sh
M  scripts/ops_seed_bidask_now_v1.py
M  scripts/ops_seed_tick_now_v1.py
A  scripts/ops_untracked_triage_v1.py
A  scripts/ops_web_research_evidence_hardgate_v1.sh
M  scripts/paper_live_integration_smoke_v1.sh
M  scripts/patch_recorder_use_groupkey.sh
M  scripts/patch_shioaji_login_token.sh
M  scripts/pm_refresh_board.sh
A  scripts/pm_refresh_board_and_verify.sh
A  scripts/pm_refresh_board_canonical.sh
M  scripts/pm_refresh_board_v2.py
A  scripts/project_board_guard_v2.py
M  scripts/run_daily_finance_close_pack_daily_v1.sh
A  scripts/run_daily_report_v1.sh
M  scripts/run_paper_live_smoke_suite_v1.py
M  scripts/run_recorder.sh
M  scripts/setup_git_hooks_v1.sh
M  scripts/setup_m0_recorder.sh
M  scripts/update_project_board_progress_v2.py
M  scripts/verify_pm_refresh_board_v1.sh
 M snapshots/spec_diff/spec_diff_report_diff.md
 M snapshots/spec_diff/spec_diff_report_latest.md
M  src/broker/shioaji_recorder.py
M  src/cost/cost_model_v1.py
A  src/execution/order_result_types.py
A  src/market/taifex_calendar_v1.py
M  src/oms/paper_oms_risk_safety_wrapper_v1.py
M  src/oms/paper_oms_risk_wrapper_v1.py
M  src/oms/run_paper_live_v1.py
A  src/ops/__init__.py
A  src/ops/latency/__init__.py
A  src/ops/latency/backpressure_governor.py
A  src/ops/latency/latency_budget.py
A  src/ops/learning/drift_detector_v1.py
A  src/ops/learning/governance_v1.py
A  src/research/run_stat_gate_report_v1.py
A  src/research/stat_gate_v1.py
M  src/risk/risk_engine_v1.py
M  src/safety/system_safety_v1.py
M  src/sim/run_strategies_paper_loop_v1.py
M  src/sim/run_strategies_paper_v1.py
M  src/strat/mean_reversion_v1.py
M  src/strat/strategy_base_v1.py
M  src/strat/trend_v1.py
A  src/tools/ops_seed_bidask_now_v1.py
A  tmf_policy_regress_bundle_20260219.tgz
A  tmf_policy_regress_bundle_20260219.tgz.sha256.txt
?? repo/LaunchAgents/
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
