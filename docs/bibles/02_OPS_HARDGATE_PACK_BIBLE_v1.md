# OPS HardGate + ULTRA WindowPack Bible v1 (OFFICIAL-LOCKED)

Generated: 2026-01-30 09:07:41

## Purpose
Define the non-negotiable contract for perfect window handoff:
**HardGate PASS → Pack build → ZIP+SHA256 verify → MANIFEST verify**.

## MUST-PASS HardGate (scripts/ops_audit_hardgate_v1.sh)
1) Dangerous filename scan: no newline/CR in filenames.
2) bash syntax: scripts/*.sh must pass bash -n.
3) python compile: src/**/*.py must py_compile PASS.
4) sqlite integrity_check: if runtime/data/tmf_autotrader_v1.sqlite3 exists, must return "ok".
5) launchd quick status: key labels visible in launchctl list (handoff_tick/autorestart/pm_tick/backup).
6) git status snapshot is informational only (repo may be untracked in early phase).

## Pack Build (scripts/mk_windowpack_ultra.sh)
- MUST run ops_audit_hardgate_v1.sh first; if FAIL → no pack.
- Pack root MUST contain:
  - MANIFEST_SHA256_ALL_FILES.txt
  - HANDOFF_ULTRA.md
  - handoff/HANDOFF_LOG.md (append-only; never truncate)
  - state/latest_state.json
  - state/next_step.txt
  - state/audit_report_latest.md  (copied from newest audit report)
  - repo/ snapshot (allowlist rsync; exclude .git/.venv/__pycache__/.DS_Store)
  - repo/LaunchAgents/*.plist (backup/pm_tick/autorestart/handoff_tick if exists)

## Verification (consumer side)
1) shasum -c ZIP.sha256.txt must be OK.
2) unzip and verify MANIFEST_SHA256_ALL_FILES.txt entries must all be OK.
3) audit_report_latest.md must exist in pack and be listed in manifest.

## OFFICIAL-LOCKED Policy
- This Bible is OFFICIAL-LOCKED. Any changes require a new version file with explicit rationale and changelog entry.
