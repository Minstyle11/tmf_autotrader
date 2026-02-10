# Daily Finance Close Pack Bible v1 (OFFICIAL-LOCKED)

## 目的
每天固定產出「日結包（Close Pack）」用於：
- 稽核：今天做了什麼、改了什麼、跑了什麼、結果如何
- 回放：未來可用同一份包重現當天狀態（含設定/關鍵輸出/摘要）
- 回滾：發現問題時能回到「上一次已知良好」狀態
- 交接：ULTRA ZERO-GAP 規格下，Close Pack 是每日最小完整快照

## 產物位置（固定）
- 根目錄：`runtime/ops/close_pack/`
- 每日資料夾：`runtime/ops/close_pack/CP_YYYY-MM-DD/`
- 每日壓縮包：`runtime/ops/close_pack/CP_YYYY-MM-DD.zip`
- 每日 zip sidecar：同名 `.sha256.txt`

## Close Pack 最小內容（v1）
1) **Manifest / checksums**
   - `MANIFEST_SHA256_ALL_FILES.txt`（對 CP_YYYY-MM-DD 內所有檔案做 sha256）
2) **Project board / ops index snapshot**
   - `PROJECT_BOARD.md`（當下版本）
   - `OPS_INDEX.md`（當下版本）
3) **Ops critical logs (allowlist)**
   - `runtime/logs/launchagent_pm_tick.out.log`（當下檔案）
   - `runtime/logs/launchagent_pm_tick.err.log`（當下檔案）
   - `runtime/logs/pm_log_rotate_v1.run.log`（當下檔案）
   - `runtime/logs/_archive/`（只打包「當日新產生」或「最新 N 份」；v1 先用 N=20）
4) **System / runtime metadata（最小可用）**
   - `meta_TIMESTAMP.txt`（內容包含：產生時間、主機、git commit（如有）、python 版本、重要路徑）
   - `CLOSE_PACK_SUMMARY.md`（人類可讀摘要：今日完成的 [TASK:PM]、關鍵變更、關鍵驗證結果）

## 嚴格規則
- Close Pack 必須 **可重複生成（idempotent）**：同一天多次跑，只是更新包內容/摘要，不應破壞其他鏈路
- 只允許打包 allowlist；避免把 secrets 或巨大資料誤打包
- 每個 zip 必須有 sidecar sha256（md5 不接受）
- 每次 Close Pack 生成後，必須在：
  - `OPS_INDEX.md` 追加一筆 “Close Pack v1” 條目（指向當天 summary 或 zip/sha）
  - `PROJECT_BOARD.md` 新增/勾選對應 [TASK:PM]

## 後續實作分段（先規格、再落地）
- v1a：先做腳本 `scripts/build_close_pack_v1.sh`
- v1b：加上 allowlist + secrets exclude + size guard
- v1c：加 LaunchAgent（盤後固定時間）
- v1d：把 close pack 結果餵給治理/回歸（讓每日驗證更自動）

(Generated at 2026-02-04 11:53:47)
