# PROJECT_BOARD ULTRA 治理聖經 v1.1 Patch（憲法級補丁）

> 本補丁為 v1 的憲法級增補條款；不得覆蓋 v1，只能以 patch 方式追加。  
> 目的：把「本機 hooks + CI 分支保護」正式納入憲法級強制，封死任何繞過。

---

## 1) Git Hooks（本機強制）— hooksPath 模式

### 1.1 前提
- 本 repo 設定：`git config core.hooksPath = .githooks`
- 因此 **不得使用** `pre-commit install`（pre-commit 會拒絕 hooksPath），必須使用 wrapper hook。

### 1.2 必備檔案（憲法級）
- `.githooks/pre-commit`：呼叫 `pre-commit run --hook-stage pre-commit`
- `.githooks/pre-push`：呼叫 `pre-commit run --hook-stage pre-push`
- `.pre-commit-config.yaml`：定義兩個 local hooks：

#### 規則（不可變更）
- **pre-commit stage（commit 前）**：只允許跑「不改檔」的 HardGate  
  - `python3 scripts/board_ultra_hardgate_v1.py`
- **pre-push stage（push 前）**：允許跑 refresh+verify（可能改檔）  
  - `bash scripts/pm_refresh_board_and_verify.sh`

### 1.3 pre-push 失敗（files were modified）時的唯一處置
若看到：
- `files were modified by this hook`

代表 refresh 已正確更新 board，但 Git 要你把變更納入 commit。唯一合法處置：

1) `git add docs/board/PROJECT_BOARD.md`
2) `git commit -m "BOARD: refresh"`
3) 再次 push

---

## 2) CI（伺服端強制）— 封死 --no-verify

### 2.1 必備 workflow（憲法級）
- `.github/workflows/board_gate.yml` 必須存在，並包含：
  - HardGate
  - pm_refresh_board_and_verify
  - `git diff --exit-code`（若 refresh 造成變更，CI 必須 FAIL，逼本機先 refresh+commit）

### 2.2 GitHub 分支保護（Required Status Checks）
必須在 GitHub 設定 main/master 分支規則，要求：
- `PROJECT_BOARD Gate / board-gate` 必須通過才能 merge

此規則用來封死：
- `git commit --no-verify`
- 任何繞過本機 hooks 的手段

---

## 3) 驗收步驟（逐步）/ Acceptance Steps

### A) 本機 commit gate
1) 任意 commit 前，預期會自動跑：
   - `TMF PROJECT_BOARD ULTRA HardGate ... Passed`

### B) 本機 push gate
1) 任意 push 前，預期會自動跑：
   - `refresh+verify`
2) 若提示修改檔案，依 1.3 唯一處置 add+commit 後再 push

### C) CI gate
1) Push/PR 後，GitHub Actions 必須出現 `PROJECT_BOARD Gate` 並 PASS
2) 分支保護必須要求此 check 通過才能 merge

---

## 4) 不可逾越宣告（憲法級）
- 未來任何新視窗/任何人不得要求再花回合修 PROJECT_BOARD
- 若 gate FAIL：唯一合法路徑是照本憲法流程 refresh/repair → commit → 再 push
