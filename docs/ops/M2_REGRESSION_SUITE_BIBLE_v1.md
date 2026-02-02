# M2 Regression Suite Bible v1 (TMF AutoTrader)

## Purpose
Provide a deterministic, fast regression gate to prove:
1) RiskEngineV1 core gates (daily max loss / consecutive-loss cooldown)
2) Market-quality gates (spread/volatility/liquidity)
3) Paper-live integration end-to-end smoke (OMS + risk wrapper + DB assertions)

This suite is designed to reduce trial-and-error by catching:
- Risk gate regressions (wrong codes / wrong PASS/REJECT behavior)
- Market-quality regression in meta.market_metrics interpretation
- Paper-live integration regressions (missing stop handling, missing FILLED/REJECTED traces)

## What is included
- scripts/m2_regression_risk_gates_v1.sh
  - Uses a temp copy of runtime/data/tmf_autotrader_v1.sqlite3
  - Mutates ONLY temp DB: DELETE FROM trades + inserts dummy rows that satisfy NOT NULL
  - Expected:
    - CASE A => REJECT RISK_DAILY_MAX_LOSS
    - CASE B => REJECT RISK_CONSEC_LOSS_COOLDOWN
    - CASE C => PASS OK
  - Writes:
    - runtime/logs/m2_regression_risk_gates_v1.run.<TS>.log
    - runtime/logs/m2_regression_risk_gates_v1.last.log

- scripts/m2_regression_market_quality_gates_v1.sh
  - Uses init_db() to create a clean temp DB (no dependency on live DB)
  - Places orders via PaperOMSRiskWrapperV1 with market_metrics injected
  - Expected:
    - spread_points too wide => RISK_SPREAD_TOO_WIDE
    - atr_points too high => RISK_VOL_TOO_HIGH
    - liquidity_score too low => RISK_LIQUIDITY_LOW
    - all ok => NEW or FILLED
  - Writes:
    - runtime/logs/m2_regression_market_quality_gates_v1.run.<TS>.log
    - runtime/logs/m2_regression_market_quality_gates_v1.last.log

- scripts/paper_live_integration_smoke_v1.sh
  - Seeds synthetic bidask_fop_v1 event for determinism when live recorder is absent
  - Runs src/oms/run_paper_live_v1.py
  - Asserts DB must contain:
    - >=1 FILLED order
    - >=1 REJECTED order with meta_json.risk_verdict.code present
  - Writes:
    - runtime/logs/paper_live_integration_smoke_v1.<TS>.log
    - runtime/logs/paper_live_integration_smoke_v1.last.log

- scripts/m2_regression_suite_v1.sh
  - Orchestrates the above in order (1/3, 2/3, 3/3)
  - Writes:
    - runtime/logs/m2_regression_suite_v1.last.log

## Critical shell rule (Heredoc)
Any embedded Python heredoc must end with the delimiter token at the start of a line:
- Correct:
    python3 - <<'PY'
    ...
    PY
- Wrong (breaks; shell keeps feeding lines into python):
    <spaces>PY

## How to run
- Fast full run:
    bash scripts/m2_regression_suite_v1.sh

- Individual:
    bash scripts/m2_regression_risk_gates_v1.sh
    bash scripts/m2_regression_market_quality_gates_v1.sh
    bash scripts/paper_live_integration_smoke_v1.sh

## Acceptance Steps (逐步)
1) Terminal: cd ~/tmf_autotrader
2) Run: bash scripts/m2_regression_suite_v1.sh
3) Expect console contains:
   - "[1/3] risk gates" with CASE A/B REJECT + CASE C PASS
   - "[2/3] market-quality gates" 3 rejects + 1 pass
   - "[3/3] paper-live integration smoke" PASS
   - final "PASS"
4) Verify logs exist:
   - ls -l runtime/logs/m2_regression_*_v1.last.log runtime/logs/paper_live_integration_smoke_v1.last.log
5) Quick sanity: open the last logs and confirm timestamps match your run.
6) Troubleshooting:
   - If you see "SyntaxError: cp -f ..." during risk gates:
     - You broke heredoc termination; ensure the line containing PY has no indentation and no extra chars.
   - If smoke fails DB assertions:
     - Check runtime/data/tmf_autotrader_v1.sqlite3 exists and schema matches runner expectations.
     - Ensure src/oms/run_paper_live_v1.py runs without import errors.

## Status
- As of 2026-02-02: m2_regression_suite_v1.sh PASS in local run.
