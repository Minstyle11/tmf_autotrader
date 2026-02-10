#!/usr/bin/env bash
set -euo pipefail

LOGDIR="${LOGDIR:-$HOME/tmf_autotrader/runtime/logs}"
ARCHIVE="$LOGDIR/_archive"
mkdir -p "$ARCHIVE"

RETENTION_DAYS="${RETENTION_DAYS:-7}"
MAX_PER_LOG="${MAX_PER_LOG:-200}"

# out.log rotate threshold (bytes)
OUT_MAX_BYTES="${OUT_MAX_BYTES:-1048576}"   # 1 MiB
FORCE_ROTATE="${FORCE_ROTATE:-0}"           # set 1 to force rotate when file non-empty

RUN_MAX_BYTES="${RUN_MAX_BYTES:-262144}"    # 256 KiB (pm_log_rotate_v1.run.log)
ts="$(date '+%Y%m%d_%H%M%S')"

# counters (for [STAT])
rotated="${rotated:-0}"
deleted_old="${deleted_old:-0}"
deleted_overcap="${deleted_overcap:-0}"
kept_err="${kept_err:-0}"
kept_out="${kept_out:-0}"
kept_run="${kept_run:-0}"
kept_close_err="${kept_close_err:-0}"
kept_close_out="${kept_close_out:-0}"
kept_total="${kept_total:-0}"

rotated_count=0
deleted_old=0
deleted_overcap=0

rotate_if_nonempty () {
  local f="$1"
  [[ -f "$f" ]] || return 0
  local sz
  sz="$(wc -c < "$f" | tr -d ' ')"
  [[ "$sz" -gt 0 ]] || return 0

  local base
  base="$(basename "$f")"
  cp -p "$f" "$ARCHIVE/${base}.${ts}" || true
  : > "$f"
  rotated_count=$((rotated_count+1))
  echo "[OK] rotated: $base -> _archive/${base}.${ts} (bytes=$sz)"
}

cleanup_archives () {
  local pattern="$1"

  # 1) delete files older than RETENTION_DAYS
  # print each deleted file path, and count them
  local old_list
  old_list="$(find "$ARCHIVE" -type f -name "$pattern" -mtime "+${RETENTION_DAYS}" -print 2>/dev/null || true)"
  if [[ -n "${old_list}" ]]; then
    # delete one-by-one (safer + countable)
    while IFS= read -r f; do
      [[ -n "$f" ]] || continue
      rm -f "$f" || true
      deleted_old=$((deleted_old+1))
    done <<<"$old_list"
  fi

  # 2) cap count to MAX_PER_LOG (keep newest)
  # build sorted list newest->oldest
  local list
  list="$(ls -1t "$ARCHIVE"/$pattern 2>/dev/null || true)"
  local n
  n="$(printf "%s\n" "$list" | sed '/^$/d' | wc -l | tr -d ' ')" || n=0

  if [[ "${n:-0}" -gt "$MAX_PER_LOG" ]]; then
    # delete everything after MAX_PER_LOG newest
    local victims
    victims="$(printf "%s\n" "$list" | sed '/^$/d' | tail -n "+$((MAX_PER_LOG+1))" || true)"
    if [[ -n "${victims}" ]]; then
      while IFS= read -r f; do
        [[ -n "$f" ]] || continue
        rm -f "$f" || true
        deleted_overcap=$((deleted_overcap+1))
      done <<<"$victims"
    fi
  fi
}

# --- pm_tick logs (ALLOWLIST) ---
ERR="$LOGDIR/launchagent_pm_tick.err.log"
OUT="$LOGDIR/launchagent_pm_tick.out.log"

# err: rotate when non-empty (or forced)
if [[ "${FORCE_ROTATE}" == "1" ]]; then
  rotate_if_nonempty "$ERR" || true
else
  rotate_if_nonempty "$ERR" || true
fi

# out: rotate when > OUT_MAX_BYTES, or forced when non-empty
if [[ -f "$OUT" ]]; then
  sz="$(wc -c < "$OUT" | tr -d ' ')"
  if [[ "${FORCE_ROTATE}" == "1" ]]; then
    rotate_if_nonempty "$OUT" || true
  else
    if [[ "$sz" -gt "$OUT_MAX_BYTES" ]]; then
      rotate_if_nonempty "$OUT" || true
    fi
  fi
fi


# --- daily finance close pack logs (ALLOWLIST) ---
CLOSE_ERR="$LOGDIR/daily_finance_close_pack_v1.err.log"
CLOSE_OUT="$LOGDIR/daily_finance_close_pack_v1.out.log"

# close_pack err: rotate when non-empty (or forced)
rotate_if_nonempty "$CLOSE_ERR" || true

# close_pack out: rotate when > OUT_MAX_BYTES (reuse same threshold), or forced when non-empty
if [[ -f "$CLOSE_OUT" ]]; then
  csz="$(wc -c < "$CLOSE_OUT" | tr -d ' ')"
  if [[ "${FORCE_ROTATE}" == "1" ]]; then
    rotate_if_nonempty "$CLOSE_OUT" || true
  else
    if [[ "$csz" -gt "$OUT_MAX_BYTES" ]]; then
      rotate_if_nonempty "$CLOSE_OUT" || true
    fi
  fi
fi

# retention cleanup (must run every time)
# --- run log (pm_log_rotate_v1.run.log) ---
RUN="$LOGDIR/pm_log_rotate_v1.run.log"
if [[ -f "$RUN" ]]; then
  rsz="$(wc -c < "$RUN" | tr -d ' ')"
  if [[ "$rsz" -gt "$RUN_MAX_BYTES" ]]; then
    base="$(basename "$RUN")"
    cp -p "$RUN" "$ARCHIVE/${base}.${ts}" || true
    : > "$RUN"
    echo "[OK] rotated: $base -> _archive/${base}.${ts} (bytes=$rsz)"
    rotated_count=$((rotated_count+1))
  fi
fi

cleanup_archives "launchagent_pm_tick.err.log.*"
cleanup_archives "launchagent_pm_tick.out.log.*"
cleanup_archives "pm_log_rotate_v1.run.log.*"
cleanup_archives "daily_finance_close_pack_v1.err.log.*"
cleanup_archives "daily_finance_close_pack_v1.out.log.*"

# compute kept count for these patterns

# compute kept count for these patterns
kept_err="$(ls -1 "$ARCHIVE"/launchagent_pm_tick.err.log.* 2>/dev/null | wc -l | tr -d ' ' || true)"
kept_out="$(ls -1 "$ARCHIVE"/launchagent_pm_tick.out.log.* 2>/dev/null | wc -l | tr -d ' ' || true)"
kept_run="$(ls -1 "$ARCHIVE"/pm_log_rotate_v1.run.log.* 2>/dev/null | wc -l | tr -d ' ' || true)"
kept_close_err="$(ls -1 "$ARCHIVE"/daily_finance_close_pack_v1.err.log.* 2>/dev/null | wc -l | tr -d ' ' || true)"
kept_close_out="$(ls -1 "$ARCHIVE"/daily_finance_close_pack_v1.out.log.* 2>/dev/null | wc -l | tr -d ' ' || true)"
kept_err="${kept_err:-0}"
kept_out="${kept_out:-0}"
kept_run="${kept_run:-0}"
kept_close_err="${kept_close_err:-0}"
kept_close_out="${kept_close_out:-0}"
kept_total=$((kept_err + kept_out + kept_run + kept_close_err + kept_close_out))
echo "[OK] pm_log_rotate_v1 done (RETENTION_DAYS=${RETENTION_DAYS}, MAX_PER_LOG=${MAX_PER_LOG}, OUT_MAX_BYTES=${OUT_MAX_BYTES}, FORCE_ROTATE=${FORCE_ROTATE})"
echo "[STAT] rotated=${rotated_count} deleted_old=${deleted_old} deleted_overcap=${deleted_overcap} kept=${kept_total} (err=${kept_err} out=${kept_out} run=${kept_run} close_err=${kept_close_err} close_out=${kept_close_out})"
