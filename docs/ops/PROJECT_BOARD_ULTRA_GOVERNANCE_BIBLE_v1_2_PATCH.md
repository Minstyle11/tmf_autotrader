# PROJECT_BOARD ULTRA 治理聖經 v1.2 Patch（憲法級補丁：GitHub Required Status Checks）

> 本補丁為 v1 + v1.1 的憲法級增補條款；不得覆蓋既有版本，只能以 patch 方式追加。  
> 目的：把 GitHub「Required Status Checks」配置步驟寫死，達到制度上不可繞過（封死 --no-verify / 未啟用 hooks / IDE 跳過 hooks）。

---

## 1) 絕對原則（制度強制）

- Git hooks / pre-commit（本機）屬於「降低失誤」的第一層，但**不是制度強制**。
- 制度強制必須依賴 GitHub 的「Required status checks」：  
  - **所有 required checks 必須通過才能 merge**。  
  - 這是封死繞過（含 `--no-verify`）的最終防線。

---

## 2) 必備 CI Gate（OFFICIAL）

本 repo 必須存在並維護：
- `.github/workflows/board_gate.yml`
  - job 名稱：`board-gate`
  - workflow 名稱：`PROJECT_BOARD Gate`
  - 必跑：
    1) `python3 scripts/board_ultra_hardgate_v1.py`
    2) `bash scripts/pm_refresh_board_and_verify.sh`
    3) `git diff --exit-code`（若 refresh 造成未提交變更 → CI FAIL，逼本機 refresh+commit）

---

## 3) GitHub 後台設定（憲法級 SOP）

### 3.1 前置：讓 status check 出現在可選清單（最常踩坑）
GitHub 後台的 Required status checks 清單**通常只會顯示「最近 7 天內在受保護分支（main/master）跑過的 checks」**。  
因此在你設定 required checks 之前，必須先讓 `PROJECT_BOARD Gate / board-gate` 至少在 `main/master` 跑過一次。

**唯一合法作法：**
1) 把 `.github/workflows/board_gate.yml` commit 並 push 到 `main/master`（或開 PR merge 進 `main/master`）
2) 確認 GitHub Actions 頁面看到 `PROJECT_BOARD Gate` 至少成功跑過一次
3) 再去設定 required checks

---

## 4) 設定 Required Status Checks（兩種介面擇一）

### 4.1 Rulesets（新介面）
1) Repo → Settings → Rules → Rulesets
2) 建立或編輯針對 `main/master` 的 ruleset
3) 新增規則：Required status checks
4) 勾選：`PROJECT_BOARD Gate / board-gate`
5) 儲存並啟用 ruleset

### 4.2 Branch protection rules（舊介面）
1) Repo → Settings → Branches
2) Branch protection rules → 編輯 `main/master`
3) 勾選「Require status checks to pass before merging」
4) 在清單中選擇：`PROJECT_BOARD Gate / board-gate`
5) 儲存

---

## 5) 變更工作流程名稱/Job 名稱的憲法級禁忌

- Required checks 是「以 check 名稱」綁定。
- 若你更改 workflow/job 名稱，GitHub 可能會卡在「Expected / Waiting for status…」，因為分支保護仍在等待舊 check 名稱。  
  **唯一合法處置：**
  1) 先更新 GitHub required checks 清單（移除舊 check、加入新 check）
  2) 確認新 check 在 main/master 跑過一次後才能勾選
  3) 再允許 merge

---

## 6) 驗收步驟（逐步）/ Acceptance Steps

### A) CI Gate 正常運作
1) push 或 PR 後，GitHub Actions 出現 `PROJECT_BOARD Gate`
2) job `board-gate` 必須 PASS

### B) Required checks 生效
1) 在 `main/master` 的 PR 上，未通過 `PROJECT_BOARD Gate` → GitHub 必須阻擋 merge
2) 通過後才允許 merge

### C) Drift 必須被 CI 擋下
1) 若 `pm_refresh_board_and_verify.sh` 造成 `PROJECT_BOARD.md` 改動但未 commit
2) CI 必須 FAIL 並提示「先在本機 refresh+commit」

---

## 7) 憲法級宣告（不可逾越）

- 未來任何新視窗不得再花回合修 PROJECT_BOARD
- 若 CI/required checks FAIL：唯一合法路徑是照 Bible v1/v1.1/v1.2 流程修復 → commit → 再推送
