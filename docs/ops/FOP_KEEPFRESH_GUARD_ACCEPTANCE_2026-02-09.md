# FOP KeepFresh Guard — Acceptance Evidence
- date_local: 2026-02-09 15:41:10
- log: runtime/logs/fop_keepfresh_guard.2026-02-09.log
- starts: 29
- pass_count: 12
- fail_count: 8

## last FAIL (context)
```
subscribe_ok	5
=== [ROUND 6] staleness_guard ===
bidask_fop_v1: max_ts=2026-02-09T05:35:54.654Z count_in_last120s=0
tick_fop_v1: max_ts=2026-02-09T05:35:54.652Z count_in_last120s=0
LAST120S_groups=0 now_utc=2026-02-09T07:16:25.798068+00:00 thr_utc=2026-02-09T07:14:25.798068+00:00
[WARN] still stale; sleep 10s then retry
[FAIL] still stale after retries
=== [START] 2026-02-09 15:16:53 code=TXFB6 ===
[OK] session=NIGHT hm=1516
=== [ROUND 1] recorder 90s ===
/Users/williamhsu/tmf_autotrader/.venv/lib/python3.9/site-packages/urllib3/__init__.py:35: NotOpenSSLWarning: urllib3 v2 only supports OpenSSL 1.1.1+, currently the 'ssl' module is compiled with 'LibreSSL 2.8.3'. See: https://github.com/urllib3/urllib3/issues/3020
  warnings.warn(
2026-02-09 15:16:53.989 | WARNING  | importlib._bootstrap:_call_with_frames_removed:228 - Optional: pip install shioaji[speed] or uv add shioaji --extra speed for better performance.
```

## last PASS (context)
```
session_stop	34
subscribe_ok	14
=== [ROUND 1] staleness_guard ===
bidask_fop_v1: max_ts=2026-02-09T07:40:33.210Z count_in_last120s=336
tick_fop_v1: max_ts=2026-02-09T07:40:30.857Z count_in_last120s=49
LAST120S_groups=2 now_utc=2026-02-09T07:40:34.233653+00:00 thr_utc=2026-02-09T07:38:34.233653+00:00
[PASS] fresh within 120s; exit 0
```
