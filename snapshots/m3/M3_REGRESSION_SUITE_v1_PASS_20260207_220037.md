# M3 REGRESSION SUITE v1 PASS SNAPSHOT

- ts_local: 2026-02-07T22:00:37+08:00
- db: runtime/data/tmf_autotrader_v1.sqlite3
- result: PASS

## Included checks (PASS)
- reject policy v1
- spec-diff stopper v1 (bidask_fop_v1 schema)
- paper-live smoke combo v1 (STRICT allow_stale=0; OFFLINE reset cooldown; OFFLINE allow_stale=1)
- taifex preflight v1
- taifex split v1
- spec os v1 (diff stopper rc=2 acceptable)
- audit+replay os v1
- reconcile os v1 (orphan fills detection)
- latency+backpressure os v1

## Notes
- STRICT mode correctly blocks stale feed (SAFETY_FEED_STALE -> COOLDOWN)
- OFFLINE mode allows stale (OK_DEV_ALLOW_STALE) while still enforcing RISK_STOP_REQUIRED
- cooldown reset via request_cooldown(seconds=0) verified in combo runner
