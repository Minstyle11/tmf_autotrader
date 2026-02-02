# ULTRA ZERO-GAP HANDOFF BIBLE v1 (OFFICIAL)

## Scope
This bible defines **non-negotiable** operating rules for TMF AutoTrader window handoff and per-turn workflow.
It is **Bible-level** (same priority class as v18). Any conflict must be resolved in favor of:
1) TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18.md mainline
2) This Bible v1 (ULTRA ZERO-GAP + Web-Search-First)

## Iron Rules (Bible-level)
### R1 — Web-Search-First Every Turn
For **every** development/design/debug/validation turn: MUST first search domestic + international web resources, then filter/summarize/analyze, and only then provide executable steps.

### R2 — ULTRA ZERO-GAP Pack Only
All future handoffs MUST be **ULTRA ZERO-GAP**:
- In the new window, the user uploads **ZIP + SHA256 sidecar only**.
- User pastes **nothing else** (no opening prompt, no extra context).
- Assistant must resume **0 discontinuity**, continuing as if still in the same window.

### R3 — Opening Prompt Is Sealed in ZIP
The opening prompt is **sealed inside the pack**. The user must NOT paste it.
Emergency-only fallback: `runtime/handoff/state/NEW_WINDOW_CLIPBOARD_ULTRA_ZH.txt`.

## Canonical Runner Entrypoint
To prevent path mistakes, we enforce a canonical entrypoint at repo root:
- `./m3_mainline_runner_v1.sh`  (root shim; stable)
- Actual implementation lives at: `./scripts/m3_mainline_runner_v1.sh`

This eliminates errors like:
- `bash: ./m3_mainline_runner_v1.sh: No such file or directory` (when user forgets `scripts/`)

## ULTRA Pack Contract (Minimum Required Artifacts)
A valid ULTRA ZERO-GAP pack MUST include:
- `MANIFEST_SHA256_ALL_FILES.txt`
- `handoff/HANDOFF_LOG.md`
- `state/NEW_WINDOW_ONESHOT_HARDGATE_SOP.txt`
- `state/env_rebuild_report_latest.md`
- `state/audit_report_latest.md`
- `state/next_step.txt`
- `state/NEW_WINDOW_OPENING_PROMPT_ULTRA_ZH.md` + sidecar
- `state/NEW_WINDOW_CLIPBOARD_ULTRA_ZH.txt` + sidecar
- `state/latest_state.json`
And must pass:
- Zip sha256 == sidecar
- Env hardgate OK
- OneShot HardGate SOP runnable in new window

## Acceptance Steps (逐步)
### A. In current window (pack build)
1) Run the canonical runner:
   - `./m3_mainline_runner_v1.sh`
2) Confirm output contains:
   - `=== [M3 MAINLINE v1] PASS ...`
   - `=== [OK] BUILT === ... TMF_AutoTrader_WindowPack_ULTRA_*.zip`
   - `[CHECK] zip_sha256_expected == zip_sha256_actual`
3) Identify latest pack paths:
   - `runtime/handoff/latest/TMF_AutoTrader_WindowPack_ULTRA_*.zip`
   - `...zip.sha256.txt`

### B. New window (UPLOAD ONLY)
1) Upload exactly two files:
   - latest `...ULTRA_*.zip`
   - its `...ULTRA_*.zip.sha256.txt`
2) Paste nothing else.
3) Assistant must instruct to run OneShot HardGate per:
   - `state/NEW_WINDOW_ONESHOT_HARDGATE_SOP.txt`
4) After HardGate PASS, continue strictly following `state/next_step.txt`.

### C. Emergency
If upload fails, paste:
- `runtime/handoff/state/NEW_WINDOW_CLIPBOARD_ULTRA_ZH.txt` contents
