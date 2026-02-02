# NEW WINDOW OPENING PROMPT (FINAL, AUTO-UPDATED)

## Current status (Board head)

```text
# 專案進度總覽（自動計算）
- 更新時間：2026-02-02 10:17:57
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
- [2026-02-02 09:07:54] pm_tick
- [2026-02-02 09:12:55] pm_tick
- [2026-02-02 09:17:55] pm_tick
- [2026-02-02 09:22:55] pm_tick
- [2026-02-02 09:27:55] pm_tick
- [2026-02-02 09:32:55] pm_tick
- [2026-02-02 09:37:55] pm_tick
- [2026-02-02 09:42:56] pm_tick
- [2026-02-02 09:47:56] pm_tick
- [2026-02-02 09:52:56] pm_tick
- [2026-02-02 09:57:56] pm_tick
- [2026-02-02 10:02:56] pm_tick
- [2026-02-02 10:07:56] pm_tick
- [2026-02-02 10:12:56] pm_tick
- [2026-02-02 10:17:57] pm_tick
```

## Working tree (git status --porcelain)

```text
?? .gitignore
?? DPB/
?? MANIFEST_SHA256_ALL_FILES.txt
?? README.md
?? TXF/
?? "Walk-forward\357\274\210\346\273\276\345\213\225\350\250\223\347\267\264/"
?? broker/
?? calendar/
?? "canary\357\274\232\351\231\220\345\217\243\346\225\270/"
?? configs/
?? contracts/
?? docs/
?? execution/
?? ops/
?? repo/
?? research/
?? risk/
?? "runbook\357\274\232connectivity/"
?? runtime/
?? schemas/
?? scripts/
?? shioaji.log
?? snapshots/
?? spec/
?? src/
?? "urgency\357\274\210low/"
?? "\344\270\200\351\215\265\351\207\215\346\224\276\357\274\210replay\357\274\211\344\273\273\346\204\217\344\270\200\345\244\251\357\274\210\345\220\253\344\270\213\345\226\256/"
?? "\344\270\213\345\226\256/"
?? "\344\274\221\345\270\202\357\274\210\345\234\213\345\256\232\345\201\207\346\227\245/"
?? "\345\210\270\345\225\206\351\231\220\345\210\266\357\274\210\346\270\254\350\251\246/"
?? "\345\213\225\346\205\213\346\255\242\346\220\215/"
?? "\345\240\261\345\203\271\344\270\255\346\226\267/"
?? "\345\244\232\351\207\215\346\257\224\350\274\203\350\252\277\346\225\264\357\274\210\344\275\240\350\251\246\344\272\206\345\244\232\345\260\221\347\265\204\345\217\203\346\225\270/"
?? "\345\244\232\351\242\250\346\240\274\357\274\210Trend/"
?? "\346\230\216\347\242\272\350\262\273\347\224\250\357\274\232\346\211\213\347\272\214\350\262\273\343\200\201\346\234\237\344\272\244\346\211\200\350\262\273\347\224\250/"
?? "\346\234\237\350\262\250/"
?? "\346\234\254\346\251\237\347\206\261\351\215\265/"
?? "\347\240\224\347\251\266/"
?? "\350\213\245\350\241\214\346\203\205\344\270\215\345\217\257\347\224\250\357\274\232\347\246\201\346\255\242\351\226\213\346\226\260\345\200\211\343\200\201\345\217\252\345\205\201\350\250\261\346\270\233\345\200\211/"
?? "\350\250\202\345\226\256\347\255\226\347\225\245\357\274\210\344\273\245\343\200\214\351\231\215\344\275\216\346\213\222\345\226\256/"
?? "\350\255\211\345\210\270/"
?? "\351\232\261\345\220\253\346\210\220\346\234\254\357\274\232spread\343\200\201slippage\343\200\201impact\357\274\210\351\232\250\346\263\242\345\213\225/"
?? "\351\242\250\351\232\252\351\240\220\347\256\227\347\250\213\345\274\217\345\214\226\357\274\232\346\257\217\347\255\226\347\225\245\346\227\245\350\231\247/"
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
