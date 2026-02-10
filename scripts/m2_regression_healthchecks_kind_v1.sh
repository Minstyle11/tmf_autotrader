#!/usr/bin/env bash
set -euo pipefail

DB="${TMF_DB_PATH:-runtime/data/tmf_autotrader_v1.sqlite3}"
if [ ! -f "$DB" ]; then
  echo "[FATAL] missing DB: $DB" >&2
  exit 2
fi

echo "=== [RG] health_checks.kind schema guard ==="
# 1) schema must contain kind
HAS_KIND="$(sqlite3 "$DB" "SELECT COUNT(*) FROM pragma_table_info('health_checks') WHERE name='kind';")"
if [ "$HAS_KIND" != "1" ]; then
  echo "[FAIL] health_checks.kind column missing (HAS_KIND=$HAS_KIND)" >&2
  sqlite3 "$DB" ".schema health_checks" || true
  exit 3
fi
echo "[OK] kind column exists"

# 2) kind must never be NULL/empty (global guard)
BAD="$(sqlite3 "$DB" "SELECT COUNT(*) FROM health_checks WHERE kind IS NULL OR trim(kind)='';")"
if [ "$BAD" != "0" ]; then
  echo "[FAIL] found NULL/empty kind rows: $BAD" >&2
  echo "=== [BAD sample top 20] ==="
  sqlite3 -separator '|' "$DB" "SELECT id, ts, kind, check_name, status FROM health_checks WHERE kind IS NULL OR trim(kind)='' ORDER BY id DESC LIMIT 20;"
  exit 4
fi
echo "[OK] null_or_empty_kind=0"

echo "=== [LAST 10] ==="
sqlite3 -header -column "$DB" "SELECT id, ts, kind, check_name, status FROM health_checks ORDER BY id DESC LIMIT 10;"

echo "=== [PASS] m2_regression_healthchecks_kind_v1 OK ==="
