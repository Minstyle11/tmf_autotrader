#!/usr/bin/env bash
set -euo pipefail

mkdir -p runtime/logs runtime/tmp
ts="$(date +%Y%m%d_%H%M%S)"

# mktemp template: XXXXXX must be at end; mktemp creates the file and returns its path
tmp_log="$(mktemp -p runtime/logs "smoke_all_v1.${ts}.XXXXXX")"
LOG="${tmp_log}.log"
mv -f "$tmp_log" "$LOG"

# mirror stdout/stderr to log
exec > >(tee -a "$LOG") 2>&1

echo "=== [SMOKE_ALL] start ts=${ts} ==="
echo "[LOG]=${LOG}"
echo

# ---- Isolated tmp DB per run (prevents cooldown/state contamination across runs) ----
BASE_DB="${TMF_DB_PATH:-runtime/data/tmf_autotrader_v1.sqlite3}"

if [[ ! -f "$BASE_DB" ]]; then
  echo "[FATAL] base db missing: $BASE_DB"
  exit 2
fi

TMP_DB_STRICT="runtime/tmp/smoke_${ts}_strict_$$.sqlite3"
TMP_DB_OFFLINE="runtime/tmp/smoke_${ts}_offline_$$.sqlite3"

cp -p "$BASE_DB" "$TMP_DB_STRICT"
cp -p "$BASE_DB" "$TMP_DB_OFFLINE"

echo "[DB_STRICT]=${TMP_DB_STRICT} (copied from ${BASE_DB})"
echo "[DB_OFFLINE]=${TMP_DB_OFFLINE} (copied from ${BASE_DB})"
echo

echo "=== [SMOKE] Risk gates smoke (DB-seeded deterministic) ==="
export TMF_DB_PATH="$TMP_DB_STRICT"
python3 src/risk/run_risk_gates_smoke_v1.py
echo

echo ""
echo "=== [SEED] fresh bidask into copied DBs (avoid stale in-session; deterministic smoke) ==="
# NOTE: during in-session (08:45–13:45) HARDGUARD disables stale override, so we must seed fresh bidask.
# Use a stable pair; price level doesn\x27t matter for safety gates, only recency + shape.
python3 scripts/ops_seed_bidask_now_v1.py --db "$TMP_DB_STRICT"  --code TMFB6 --bid 31774 --ask 31775 --clear-cooldown=1 >/dev/null
python3 scripts/ops_seed_bidask_now_v1.py --db "$TMP_DB_OFFLINE" --code TMFB6 --bid 31774 --ask 31775 --clear-cooldown=1 >/dev/null
echo "=== [SEED] done ==="
echo "=== [SMOKE] Paper-live smoke (offline/after-hours safe defaults) ==="
overall_rc=0

echo "=== [RUN] STRICT (default) ==="
export TMF_DB_PATH="$TMP_DB_STRICT"
export TMF_DEV_ALLOW_STALE_BIDASK="0"
export TMF_MAX_BIDASK_AGE_SECONDS="${TMF_MAX_BIDASK_AGE_SECONDS:-15}"
export TMF_REQUIRE_SESSION_OPEN="${TMF_REQUIRE_SESSION_OPEN:-0}"
python3 -u src/oms/run_paper_live_v1.py --db "$TMF_DB_PATH"
rc=$?
if [[ "$rc" -ne 0 ]]; then overall_rc=$rc; fi
echo "=== STRICT_OK ==="
echo

echo "=== [RUN] OFFLINE_OVERRIDE (allow stale) ==="
export TMF_DB_PATH="$TMP_DB_OFFLINE"
export TMF_DEV_ALLOW_STALE_BIDASK="1"
export TMF_MAX_BIDASK_AGE_SECONDS="${TMF_MAX_BIDASK_AGE_SECONDS:-15}"
export TMF_REQUIRE_SESSION_OPEN="${TMF_REQUIRE_SESSION_OPEN:-0}"
python3 -u src/oms/run_paper_live_v1.py --db "$TMF_DB_PATH"
rc=$?
if [[ "$rc" -ne 0 ]]; then overall_rc=$rc; fi
echo "=== OFFLINE_OVERRIDE_OK ==="
echo

rc=$overall_rc

echo
echo "[RC]=${rc}"
if [[ "$rc" -eq 0 ]]; then
  echo "=== [OK] SMOKE ALL PASS ==="
else
  echo "=== [FAIL] SMOKE ALL FAIL rc=${rc} ==="
fi

if [[ "${TMF_SMOKE_KEEP_TMPDB:-0}" == "1" ]]; then
  echo "[KEEP] TMP_DB_STRICT=${TMP_DB_STRICT}"
  echo "[KEEP] TMP_DB_OFFLINE=${TMP_DB_OFFLINE}"
else
  rm -f "$TMP_DB_STRICT" "$TMP_DB_OFFLINE" || true
  echo "[CLEAN] removed TMP_DB_STRICT + TMP_DB_OFFLINE"
fi

exit "$rc"
