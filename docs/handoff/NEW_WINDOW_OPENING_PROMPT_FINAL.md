# NEW WINDOW OPENING PROMPT (FINAL, AUTO-UPDATED)

## Current status (Board head)

```text
# 專案進度總覽（自動計算）
- 更新時間：2026-02-02 17:48:13
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
```

## Latest changes (Changelog tail)

```text
- [2026-02-02 16:38:11] pm_tick
- [2026-02-02 16:43:11] pm_tick
- [2026-02-02 16:48:11] pm_tick
- [2026-02-02 16:53:11] pm_tick
- [2026-02-02 16:58:11] pm_tick
- [2026-02-02 17:03:12] pm_tick
- [2026-02-02 17:08:12] pm_tick
- [2026-02-02 17:13:12] pm_tick
- [2026-02-02 17:18:12] pm_tick
- [2026-02-02 17:23:12] pm_tick
- [2026-02-02 17:28:12] pm_tick
- [2026-02-02 17:33:13] pm_tick
- [2026-02-02 17:38:13] pm_tick
- [2026-02-02 17:43:13] pm_tick
- [2026-02-02 17:48:13] pm_tick
```

## Working tree (git status --porcelain)

```text

```

## Next terminal step (runtime/handoff/state/next_step.txt)

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
from pathlib import Path

p = Path("src/oms/run_paper_live_v1.py")
print("exists=", p.exists())
if p.exists():
    txt = p.read_text(encoding="utf-8", errors="replace")
    print(txt[:1600])
PY2

echo "=== [TODO] Implement MarketMetricsProviderV1 + wire into run_paper_live_v1.py meta.market_metrics ==="
```

## Rules (must follow)
- One terminal command per turn.
- Append-only logs; no silent rewrites.
- One-Doc/One-Truth: TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18.md.
