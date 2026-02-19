# OPS Runbook v1 (TMF AutoTrader)

## Daily/On-demand checks
1) Healthcheck
- Command: `cd ~/tmf_autotrader && ./scripts/m0_healthcheck_v1.sh`
- Trading bucket strict check: `STRICT_SESSION=1 ./scripts/m0_healthcheck_v1.sh`

2) Pipeline one-shot (recorder→ingest→norm→bars)
- Command: `cd ~/tmf_autotrader && MAX_SECONDS=30 ./scripts/m0_pipeline_one.sh`

3) Auto backup
- LaunchAgent: `com.tmf_autotrader.backup`
- Logs:
  - `runtime/logs/backup.out.log`
  - `runtime/logs/backup.err.log`

4) Auto PM tick
- LaunchAgent: `com.tmf_autotrader.pm_tick`
- Logs:
  - `runtime/logs/launchagent_pm_tick.out.log`
  - `runtime/logs/launchagent_pm_tick.err.log`

5) Auto-restart (this doc)
- LaunchAgent: `com.tmf_autotrader.autorestart`
- Logs:
  - `runtime/logs/autorestart.out.log`
  - `runtime/logs/autorestart.err.log`
  - `runtime/logs/autorestart.pipeline.log`
  - `runtime/logs/autorestart.last_healthcheck.log`
