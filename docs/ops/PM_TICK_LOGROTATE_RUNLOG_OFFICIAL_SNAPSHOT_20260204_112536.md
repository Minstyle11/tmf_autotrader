# PM Tick Logrotate v1 — RunLog Rotation + STAT(run=) OFFICIAL Snapshot

## Scope
This snapshot covers:
- `scripts/pm_log_rotate_v1.sh` rotates and retains:
  - `runtime/logs/launchagent_pm_tick.out.log`
  - `runtime/logs/launchagent_pm_tick.err.log`
  - `runtime/logs/pm_log_rotate_v1.run.log` (run log)
- `scripts/pm_refresh_board.sh` invokes logrotate hook with pinned env, append-only run log.
- `[STAT]` line includes `run=` (kept_run) and uses `rotated_count`.

## Key Behavior (as implemented)
- Rotate `launchagent_pm_tick.out.log` when size > `OUT_MAX_BYTES` (default 1 MiB) unless `FORCE_ROTATE=1`.
- Rotate `launchagent_pm_tick.err.log` when non-empty (or forced).
- Rotate `pm_log_rotate_v1.run.log` when size > `RUN_MAX_BYTES` (1 MiB).
- Retention policy:
  - delete archives older than `RETENTION_DAYS`
  - cap per-log archives to `MAX_PER_LOG` newest
- Metrics:
  - `rotated_count` increments for each rotation (including run.log rotation)
  - `kept_total` includes `kept_err + kept_out + kept_run`
  - STAT format includes `run=<kept_run>`

## Evidence (smoke)
- `pm_log_rotate_v1.run.log` tail shows STAT includes `run=...`:
  - `[STAT] ... (err=0 out=2 run=3)` observed on 2026-02-04.

## Files
- scripts/pm_log_rotate_v1.sh
- scripts/pm_refresh_board.sh
- runtime/logs/pm_log_rotate_v1.run.log
- runtime/logs/_archive/pm_log_rotate_v1.run.log.*
- runtime/logs/_archive/launchagent_pm_tick.*.log.*

