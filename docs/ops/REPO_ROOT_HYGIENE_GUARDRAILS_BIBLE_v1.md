# REPO_ROOT_HYGIENE_GUARDRAILS_BIBLE_v1

- time: 2026-02-02
- scope: tmf_autotrader repo root hygiene / quarantine guardrails
- goal: prevent any future "canonical moved into quarantine" incidents

## 0) Non-negotiables
1) **Never delete.** Only MOVE into `runtime/quarantine/...` (append-only).
2) **Never touch canonical trees** without an explicit allowlist match:
   - MUST-NOT-MOVE prefixes (recursive): `docs/`, `runtime/`, `src/`, `scripts/`, `spec/`, `schemas/`, `configs/`, `contracts/`, `execution/`, `repo/`, `TXF/`, `DPB/`, `broker/`, `calendar/`, `ops/`, `research/`, `risk/`, `snapshots/`
3) Any hygiene action MUST be:
   - `MOVE_PLAN.md` generated first
   - then `MOVE_LOG.md` after, with exact src->dest lines
   - and post-check assertions (e.g., "repo root has no backtick entries")

## 1) Allowed automated moves (SAFE-AUTO)
Only the following pattern is allowed for fully automated move:
- **Repo-root entries whose NAME starts with a backtick**: `` `* ``
  - Tool: `scripts/repo_root_hygiene_backtick_quarantine_v1.sh`
  - Rule: `find -maxdepth 1 -name '\`*'` only.

Everything else is **manual review** (SAFE-REVIEW) unless a future Bible explicitly expands SAFE-AUTO with tests.

## 2) Restore procedure (if anything important is missing)
If a critical file disappears, restore from quarantine **without deleting quarantine**:
- Identify the newest quarantine dir:
  - `ls -1dt runtime/quarantine/scaffold_noise_* | head`
- Restore (example):
  - `rsync -a <QUAR_DIR>/ ./`
- Verify critical files (must exist):
  - `docs/board/PROJECT_BOARD.md`

## 3) Post-run verification checklist
After any hygiene move:
1) `docs/board/PROJECT_BOARD.md` exists
2) repo root has **no** backtick entries: `find . -maxdepth 1 -name '\`*' -print`
3) canonical dirs still exist: `calendar ops research risk docs runtime scripts src`
4) quarantine contains MOVE_PLAN + MOVE_LOG for the action

## 4) Incident record (2026-02-01/02)
- Symptom: canonical content (incl. `docs/board/PROJECT_BOARD.md`) was moved into `runtime/quarantine/...`
- Recovery: restored via rsync from quarantine back to repo root
- Preventive fix: enforce SAFE-AUTO = backtick-only, and protect canonical trees via MUST-NOT-MOVE list
