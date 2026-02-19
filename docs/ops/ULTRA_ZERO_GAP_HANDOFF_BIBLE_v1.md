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

---

## HARDGATE：Pack Manifest 嚴格驗收（排除 manifest 自我行）v1

**狀態：OFFICIAL / 憲法等級 / 不可違逆**
最後更新：2026-02-03 00:56:09 +0800

### 為什麼要排除「MANIFEST_SHA256_ALL_FILES.txt」自己的那一行？
若 manifest 內容包含它自己的 checksum 行，則在重算/比對時會出現「自我引用」不動點問題：
manifest 內容一變 → manifest 檔案的 hash 就變 → 那行 checksum 也必然改變 → 永遠 mismatch。
**因此規則固定：manifest 的 checksum 清單必須排除 manifest 檔案本身。**

### ULTRA 打包必做事項（HARDGATE-STRICT）

#### A. 建包前（Pre-Build）
1. 確認 repo clean / commits 完整（必要變更需已 commit）。
2. 確認本次要納入的 runtime artifacts 範圍（sqlite snapshot、最新 raw_events、必要 logs）。

#### B. 建包（Build）
1. 產生/更新 sqlite snapshot（例如 VACUUM INTO）。
2. 拷貝工作集到 pack 目錄（排除 `.git/` 與超大 raw_events 歷史）。
3. **重建 `MANIFEST_SHA256_ALL_FILES.txt`（嚴格規則：排除 manifest 自己 + 建議排除 `.DS_Store`）**
   - manifest 內容格式固定：`<sha256>␠␠<relative_path>`
   - 排除規則：
     - `MANIFEST_SHA256_ALL_FILES.txt`
     - `**/.DS_Store`（避免 OS 垃圾造成不穩定）

4. 產生 ZIP。
5. 產生 ZIP sidecar：`<zip>.sha256.txt`

#### C. 驗收（Verify / HARDGATE-STRICT）
1. **ZIP SHA256 sidecar 驗證**
   - `shasum -a 256 <zip>` 必須與 sidecar 一致。
2. **UNZIP 到 temp**
3. **manifest strict 驗證（核心）**
   - 以解壓後內容「重算」所有檔案 sha256
   - **重算時一律排除 manifest 本身**（同 Build 規則）
   - 逐行比對「in-zip manifest」與「recalc manifest」
   - 允許差異：**零**（strict）
4. 若發生 mismatch，先判斷是否僅因「manifest 自我行」造成：
   - 若是：**重建 manifest（排除自我行）→ 更新 ZIP 內 manifest → 重建 zip sidecar → 再跑一次 strict hardgate**
   - 若否：視為 FAIL，禁止交接（必須修到 PASS 才能交接）

#### D. 交接保證（ULTRA ZERO-GAP）
- 新視窗只需附：`<WindowPack>.zip` + `<WindowPack>.zip.sha256.txt`
- 新視窗不得要求使用者補充說明；必須能 **100% 從 pack 內資料恢復上下文、狀態、規則、進度、驗收證據**。

## ULTRA_HARDGATE_STRICT_V1_20260203
（憲法級必做）每次產生 ULTRA WindowPack **必須**完成以下驗收，且全數 PASS 才能視為可交接：

### HARDGATE-1：ZIP sidecar sha256
- 驗收：zip.sha256.txt 與 zip 實際 sha256 必須一致

### HARDGATE-2：解壓到 temp
- 驗收：unzip 成功，且 unpack_root 正確

### HARDGATE-3：MANIFEST 必須存在於 pack root
- 驗收：{"<unpack_root>"}/MANIFEST_SHA256_ALL_FILES.txt 必須存在

### HARDGATE-4：MANIFEST 禁止 self-line
- 驗收：MANIFEST 內容不得包含 `MANIFEST_SHA256_ALL_FILES.txt` 自己那一行（避免自我指涉導致必然 mismatch）

### HARDGATE-5：strict recompute + compare
- 驗收：以 unpack_root 為 root 重新計算所有檔案 sha256（排除 manifest 本身）後，必須與 MANIFEST 完全一致
- 期望輸出：`[PASS] strict manifest match (exclude self)`

### 結論
- 只有當以上 1~5 全 PASS，該 ZIP 才允許作為「新視窗零輸入 0 斷層」交接包。
- 任何 FAIL → 立刻視為封存失敗，必須修復後重打包重驗收。


## ULTRA HARDGATE STRICT PASS (NO MANIFEST LINES)
- ts: 2026-02-03T11:05:05+08:00
- zip: /Users/williamhsu/tmf_autotrader/runtime/handoff/latest/TMF_AutoTrader_WindowPack_ULTRA_20260203_092328.zip
- sha256: 5cee5b731c90a0d7ebea80ebc4a5551d34c6343549f27427787e8f2cf2b03b37
- hardgate: sidecar OK; unzip OK; pack-root manifest OK; manifest contains ZERO 'MANIFEST_SHA256_ALL_FILES.txt' lines; strict recompute+compare PASS
