#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

VENV_PY="./.venv/bin/python"
DB="runtime/data/tmf_autotrader_v1.sqlite3"
MIN_NON_SYS="${MIN_NON_SYS:-50}"
MIN_TICKS="${MIN_TICKS:-20}"

echo "=== [1] recorder MAX_SECONDS=${MAX_SECONDS:-0} ==="
./scripts/run_recorder.sh

echo "=== [2] locate latest raw_events_*.jsonl ==="
LATEST="$(ls -1t runtime/data/raw_events_*.jsonl 2>/dev/null | head -n 1 || true)"
if [[ -z "${LATEST}" ]]; then
  echo "[FATAL] no runtime/data/raw_events_*.jsonl found" >&2
  exit 2
fi
echo "[OK] latest=${LATEST}"

echo "=== [2.1] validate latest has tick + market events ==="
TICKS="$("${VENV_PY}" - "${LATEST}" <<'PY'
import json, sys
p=sys.argv[1]
n=0
with open(p,'r',encoding='utf-8') as f:
  for line in f:
    line=line.strip()
    if not line: continue
    try:
      o=json.loads(line)
      k=str(o.get('kind',''))
      if k.startswith('tick_'): n+=1
    except Exception:
      pass
print(n)
PY
)"
NON_SYS="$("${VENV_PY}" - "${LATEST}" <<'PY'
import json, sys
p=sys.argv[1]
n=0
with open(p,'r',encoding='utf-8') as f:
  for line in f:
    line=line.strip()
    if not line: continue
    try:
      o=json.loads(line)
      k=str(o.get('kind',''))
      if not k.startswith('session_'): n+=1
    except Exception:
      pass
print(n)
PY
)"
echo "[INFO] tick_events=${TICKS} (min=${MIN_TICKS})"
echo "[INFO] non_sys_events=${NON_SYS} (min=${MIN_NON_SYS})"
if [[ "${MIN_NON_SYS}" -gt 0 && "${NON_SYS}" -lt "${MIN_NON_SYS}" ]]; then
  echo "[FATAL] latest raw_events has too few market events; likely out-of-session. Rerun during market hours or set MIN_NON_SYS=0 to bypass." >&2
  exit 3
fi
if [[ "${MIN_TICKS}" -gt 0 && "${TICKS}" -lt "${MIN_TICKS}" ]]; then
  echo "[FATAL] latest raw_events has too few tick_* events; recorder likely out-of-session or too short. Increase MAX_SECONDS or run during market hours, or set MIN_TICKS=0 to bypass." >&2
  exit 4
fi

echo "=== [3] ingest latest -> DB ==="
"${VENV_PY}" -u src/data/store_sqlite_v1.py "${DB}" "${LATEST}"

echo "=== [4] normalize events -> norm_ticks ==="
"${VENV_PY}" -u src/data/normalize_events_v1.py

echo "=== [5] build 1m bars ==="
"${VENV_PY}" -u src/data/build_bars_1m_v1.py

echo "=== [6] healthcheck ==="
./scripts/m0_healthcheck_v1.sh
