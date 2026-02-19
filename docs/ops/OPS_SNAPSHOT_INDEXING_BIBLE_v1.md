# OPS Snapshot Indexing Bible v1 (OFFICIAL-LOCKED)

## 目的
把所有 ops 類文件（例如 logrotate、runlog、launchagent、backup、daily close pack、healthcheck…）的「狀態快照」納入可稽核鏈：
- 每份 ops 快照都要有 **md + sha256 sidecar**
- 由 **OPS_INDEX.md** 統一彙整（index-like single entry point）
- 同步在 **PROJECT_BOARD.md** 新增/勾選對應的 [TASK:PM]（讓完成度統計能反映）

## 檔名規範
- 快照：`docs/ops/<NAME>_OFFICIAL_SNAPSHOT_YYYYMMDD_HHMMSS.md`
- Sidecar：同名加 `.sha256.txt`（內容：`<sha256>  <filename>`）
- 索引：`docs/ops/OPS_INDEX.md`（列出 ops 快照清單）

## 必做步驟（每次新增 ops 快照）
1) 生成快照 md（內容要「能獨立重現當時狀態」，包含必要路徑/設定/重點驗證結果）
2) 生成 sidecar sha256（sha256 of md）
3) 更新 `docs/ops/OPS_INDEX.md`
   - 新增一行指向：快照 md + sidecar
   - 若是索引自身（OPS_INDEX）有變動，也要再做一次 OPS_INDEX 的 OFFICIAL snapshot（閉環）
4) 更新 `docs/board/PROJECT_BOARD.md`
   - 插入/勾選一條 `[TASK:PM]`，描述清楚「做了什麼 snapshot」，並附上 md 路徑
5) 執行 `scripts/pm_refresh_board_canonical.sh <tag>` 讓 header 統計立即更新
6) 最後 smoke：
   - grep OPS_INDEX 是否含新條目
   - grep PROJECT_BOARD 是否含 TASK
   - 確認 sha256 sidecar 存在且格式正確

## 允許清單（目前納入 rotation/retention 的 logs）
- `runtime/logs/launchagent_pm_tick.out.log`
- `runtime/logs/launchagent_pm_tick.err.log`
- `runtime/logs/pm_log_rotate_v1.run.log`
- archive dir：`runtime/logs/_archive/`

## 原則
- **追加優先（append-only）**：除非修正錯誤，盡量不要覆蓋既有快照內容
- **最小侵入**：不改動主線功能，只補治理/可觀測性/可稽核鏈
- **可自動化必自動化**：能用腳本做的不要靠手工

(Generated at 2026-02-04 11:50:21)
