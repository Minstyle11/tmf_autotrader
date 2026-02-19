# HEALTH_CHECKS.kind + paper_smoke_suite_v1 修正封存（BIBLE v1）

## 背景
- health_checks 表原本無 kind 欄位，部分工具/查詢使用 `select ... kind ...` 造成錯誤：`no such column: kind`
- 目標：在不破壞既有資料前提下，加入 kind 並回填；同時修正 paper smoke suite 寫入 DB 的 SQL/參數順序與括號錯誤，確保後續永遠寫入 kind。

## DB Schema（health_checks）
- 新增欄位：`kind TEXT NULL`
- 回填策略：`kind = check_name`（至少對 smoke suite 此類檢查等價且穩定）
- 驗證：`null_or_empty_kind = 0` 且最近 N 筆 kind 非空

## 腳本修正（scripts/run_paper_live_smoke_suite_v1.py）
- 修正 INSERT 欄位/VALUES 數量與 tuple 對齊
- 確保寫入：
  - ts
  - check_name
  - kind（= paper_smoke_suite_v1）
  - status
  - summary_json
  - out_log/err_log/meta_json（若該路徑存在）
- 必須 `py_compile` 通過

## LaunchAgent 狀態判讀（com.tmf_autotrader.paper_smoke_suite_v1）
- `state = not running`：CalendarInterval job 平時不會常駐，只有觸發/手動 kickstart 時才會 running
- `com.apple.launchd.calendarinterval: state = active`：代表觸發器已註冊
- `launchctl print-disabled ...` 中出現：
  - `"label" => enabled`：表示未被停用（disabled services 區塊是 override 表，不代表都 disabled）

## 驗收準則（Definition of Done）
1. `sqlite3 runtime/data/tmf_autotrader_v1.sqlite3 "select count(*) as null_or_empty_kind from health_checks where kind is null or trim(kind)='';"` 回傳 0
2. smoke suite 執行後，最新一筆 health_checks：
   - kind = paper_smoke_suite_v1
   - status = PASS
3. LaunchAgent：
   - enabled（print-disabled 顯示 enabled）
   - calendarinterval active
   - 手動 kickstart 可寫 log + DB
