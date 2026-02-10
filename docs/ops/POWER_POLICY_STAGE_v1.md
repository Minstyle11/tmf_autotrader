# POWER_POLICY_STAGE_v1 (OFFICIAL)

## Goal
Operate TMF AutoTrader as a stable, always-on trading appliance during trading-critical windows, while keeping development-phase risk low.

## Current Stage (as of 2026-02-08)
### AC Power (Trading Appliance Mode)
- sleep = 0
- standby = 0
- powernap = 0
- womp = 0
- tcpkeepalive = 1 (keep enabled to avoid breaking critical system features)

Rationale: prevent idle sleep on AC to reduce runtime interruption risk.

### Battery Power (Safety Mode)
- sleep = 10
- standby = 1
- powernap = 0
- womp = 0
- tcpkeepalive = 1

Rationale: allow sleep on battery to reduce risk from thermal/load and accidental unplug events.

## Promotion Rule (Stage B trigger)
When project enters "paper trading / intraday continuous smoke suite" phase, assistant must proactively remind to:
1) lock trading-hour no-sleep policy (AC) and validate with sleep/wake triage logs,
2) include sleep/wake triage in daily Finance Close Pack,
3) ensure watchdog/autorestart behavior is compatible with power state transitions.

## Packaging Rule
This file + sha256 sidecar MUST be included in every ULTRA window pack/handoff.
