# LEARNING_GOVERNANCE_V1 (OFFICIAL-LOCKED compatible)

對應：v18.1 Patch / TASK:M8-V18_1-01-74a39141
目標：drift / 非平穩 / 線上學習必須「可控、可回退、可凍結」。

## 1) 三種模式（最小可用）
- **FROZEN**（預設）：不做任何線上學習/自適應變更；照既有策略與風控執行。
- **SHADOW**：允許產生「意圖/建議」，但**不得影響下單**。所有意圖需落盤/可稽核。
- **PROMOTE**：只能在 release window 使用；必須 **canary**（限口數/限策略/限方向），並且任何 drift/風險觸發要能自動回到 FROZEN（rollback/freeze）。

## 2) 設定方式（環境變數）
- `TMF_LEARNING_MODE=FROZEN|SHADOW|PROMOTE`
- Promote canary 限制：
  - `TMF_CANARY_MAX_QTY`（預設 2.0）
  - `TMF_CANARY_ALLOW_STRATS`（逗號分隔；空=不限）
  - `TMF_CANARY_ALLOW_SIDES`（預設 BUY,SELL）

## 3) Shadow 意圖落盤位置
- `runtime/logs/learning_shadow_intents.jsonl`

## 4) Drift detector v1（fail-safe）
- 產物：`runtime/handoff/state/drift_report_latest.json`
- 目前 v1 trigger（保守）：
  - `DRIFT_SAMPLES_LOW`：最近 spread 樣本不足（預設 <60）
  - `DRIFT_SPREAD_WIDE`：最近平均 spread 過寬（預設 >2.5 點）
- 任一 trigger → **freeze**（寫入 `runtime/state/learning_governance_state.json`）

可調整參數：
- `TMF_DRIFT_SPREAD_LOOKBACK`（預設 300）
- `TMF_DRIFT_MIN_SAMPLES`（預設 60）
- `TMF_DRIFT_MAX_MEAN_SPREAD`（預設 2.5）

## 5) 驗收（必做）
1. `TMF_LEARNING_MODE=SHADOW` 跑 paper loop，確認不下單、只落 `learning_shadow_intents.jsonl`
2. `TMF_LEARNING_MODE=PROMOTE` 且 `TMF_CANARY_MAX_QTY=1`，確認超口數會被阻擋並落盤
3. 刻意把 `TMF_DRIFT_MIN_SAMPLES` 設很大（例如 9999），確認 drift detector 觸發 freeze，並寫出 drift_report_latest.json
