# M2_REGRESSION_SUITE_BIBLE_v1 (OFFICIAL)

## 0. Purpose
This Bible defines the *minimum, non-negotiable* regression gates for TMF AutoTrader v1:
- Risk gates correctness (daily loss / consecutive loss cooldown / stop required)
- Market-quality gates correctness (spread / vol / liquidity)
- Paper-live integration smoke (place -> match -> store; reject paths logged)

This suite is intended to be run before any change is considered "safe to advance".

## 1. Latest Verified PASS (evidence)
- PASS timestamp: 2026-02-03T20:52:11+08:00
- Logs:
  - runtime/logs/m2_regression_risk_gates_v1.last.log
  - runtime/logs/m2_regression_market_quality_gates_v1.last.log
  - runtime/logs/paper_live_integration_smoke_v1.last.log
  - runtime/logs/m2_regression_suite_v1.last.log
- Gov snapshot:
  - runtime/research/gov_snapshots/GOV_SNAPSHOT_20260203_205423_M2_REGRESSION_SUITE_V1_PASS.md
  - runtime/research/gov_snapshots/GOV_SNAPSHOT_20260203_205423_M2_REGRESSION_SUITE_V1_PASS.md.sha256.txt

## 2. Scope (what MUST be covered)
### 2.1 Risk gates
MUST validate:
- Daily max loss -> REJECT (RISK_DAILY_MAX_LOSS)
- Consecutive losses cooldown -> REJECT (RISK_CONSEC_LOSS_COOLDOWN)
- Cooldown expired -> PASS OK
- Stop required -> REJECT (RISK_STOP_REQUIRED) when strict_require_stop=1 and meta.stop_price missing

### 2.2 Market-quality gates
MUST validate:
- Spread too wide -> REJECT (RISK_SPREAD_TOO_WIDE)
- Vol too high -> REJECT (RISK_VOL_TOO_HIGH)
- Liquidity low -> REJECT (RISK_LIQUIDITY_LOW)
- Normal metrics -> PASS (Order object created)

### 2.3 Paper-live integration smoke
MUST validate:
- Case1 (missing stop) => rejected and stored as REJECTED in temp DB
- Case2 (has stop) => status NEW, match fills >= 1, then DB assertions ok
- Suite prints smoke_ok = True

## 3. Stale bidask policy (VERY IMPORTANT)
- Default: require recent bidask (safety gate).
- Offline smoke exception ONLY:
  - TMF_DEV_ALLOW_STALE_BIDASK=1
  - Effect: safety.require_recent_bidask=0
  - This is allowed ONLY for offline smoke/regression and must never be used in real paper-live or live.

## 4. SQLite durability note (documentation requirement)
If DB runs in WAL mode, synchronous=NORMAL is acceptable for most apps but has:
- consistency safety in WAL mode
- possible durability loss on power failure (recent commits may roll back)
This must be explicitly acknowledged in ops docs whenever PRAGMA is changed.

## 5. Acceptance Steps (逐步)
1) Run M2 regression suite (the same entrypoint that produces runtime/logs/m2_regression_suite_v1.last.log).
2) Confirm all three sections PASS:
   - risk gates PASS
   - market-quality gates PASS
   - paper-live integration smoke PASS (smoke_ok=True, db assertions ok)
3) Confirm the following files exist and are non-empty:
   - runtime/logs/m2_regression_suite_v1.last.log
   - runtime/research/gov_snapshots/GOV_SNAPSHOT_*_M2_REGRESSION_SUITE_V1_PASS.md
   - sha256 sidecar for the snapshot
4) Verify Bible sha256 sidecar:
   - sha256(docs/ops/M2_REGRESSION_SUITE_BIBLE_v1.md) matches docs/ops/M2_REGRESSION_SUITE_BIBLE_v1.md.sha256.txt
