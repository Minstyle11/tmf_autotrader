#!/usr/bin/env bash
set -euo pipefail

DB="${1:-${TMF_DB_PATH:-runtime/data/tmf_autotrader_v1.sqlite3}}"

echo "=== [RG] health_checks.summary_json smoke suite v1 guard ==="
echo "[DB] $DB"

# Pick latest row for this check
ROW="$(sqlite3 -separator '|' "$DB" "
SELECT id, ts,
       json_valid(summary_json) AS jvalid,
       json_extract(summary_json,'$.A_ok') AS A_ok,
       json_extract(summary_json,'$.B_ok') AS B_ok,
       json_extract(summary_json,'$.C_ok') AS C_ok
FROM health_checks
WHERE check_name='paper_smoke_suite_v1'
ORDER BY id DESC
LIMIT 1;
")"

echo "[ROW] id|ts|jvalid|A_ok|B_ok|C_ok = $ROW"

# Fail if JSON invalid or keys missing/not 1
BAD="$(sqlite3 "$DB" "
WITH latest AS (
  SELECT summary_json
  FROM health_checks
  WHERE check_name='paper_smoke_suite_v1'
  ORDER BY id DESC
  LIMIT 1
)
SELECT CASE
  WHEN json_valid(summary_json) != 1 THEN 1
  WHEN json_extract(summary_json,'$.A_ok') != 1 THEN 1
  WHEN json_extract(summary_json,'$.B_ok') != 1 THEN 1
  WHEN json_extract(summary_json,'$.C_ok') != 1 THEN 1
  ELSE 0
END
FROM latest;
")"

if [ "$BAD" = "0" ]; then
  echo "[PASS] latest smoke suite summary_json has A_ok/B_ok/C_ok = 1"
  exit 0
fi

echo "[FAIL] latest smoke suite summary_json missing keys or not 1" >&2
sqlite3 -header -column "$DB" "
SELECT id, ts, status, summary_json
FROM health_checks
WHERE check_name='paper_smoke_suite_v1'
ORDER BY id DESC
LIMIT 3;
" >&2 || true
exit 2
