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
