#!/bin/bash
set -euo pipefail

# WEB_RESEARCH_EVIDENCE_HARDGATE_V1
# FAIL-fast if web research evidence is missing/empty/placeholder.
#
# Expected location inside unpacked ZIP:
#   repo/runtime/handoff/state/web_research_evidence_latest.md

p="${1:-repo/runtime/handoff/state/web_research_evidence_latest.md}"

if [[ ! -f "$p" ]]; then
  echo "[FATAL] web research evidence missing: $p" >&2
  exit 41
fi

# must be non-empty and not trivially small
if [[ ! -s "$p" ]]; then
  echo "[FATAL] web research evidence empty: $p" >&2
  exit 42
fi

# placeholder sentinels (must not exist)
if /usr/bin/grep -q "MISSING_WEB_RESEARCH_EVIDENCE" "$p"; then
  echo "[FATAL] web research evidence is placeholder (must be real): $p" >&2
  exit 43
fi
if /usr/bin/grep -qE "^- q: *\\(none\\)|^- sources: *\\(none\\)|^- synthesis: *\\(none\\)" "$p"; then
  echo "[FATAL] web research evidence fields are blank/none (must be real): $p" >&2
  exit 44
fi

echo "[PASS] web research evidence hardgate OK: $p"
