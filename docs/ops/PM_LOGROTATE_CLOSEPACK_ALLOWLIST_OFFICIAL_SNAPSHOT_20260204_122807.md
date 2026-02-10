# PM_LOGROTATE CLOSEPACK ALLOWLIST OFFICIAL SNAPSHOT
- ts: 2026-02-04 12:28:07
- scope: scripts/pm_log_rotate_v1.sh allowlist for daily_finance_close_pack_v1.{out,err}.log (+ counters + STAT)
- generated_by: manual snapshot (this window)

## What changed (summary)
- Added closepack business logs to logrotate allowlist:
  - runtime/logs/daily_finance_close_pack_v1.out.log
  - runtime/logs/daily_finance_close_pack_v1.err.log
- Added counters in STAT:
  - close_err / close_out
- Verified rotation works (size > 1MiB triggers archive + truncation)

## Evidence (expected)
- After growth > OUT_MAX_BYTES, pm_log_rotate_v1 should emit:
  - `[OK] rotated: daily_finance_close_pack_v1.out.log -> _archive/... (bytes=...)`
  - STAT includes `close_out>=1` when archive exists
