# PROJECT_BOARD ULTRA 治理聖經 v1.3 Patch（憲法級補丁：Required Checks 完成證據封存）

> 本補丁為 v1 + v1.1 + v1.2 的憲法級增補條款；不得覆蓋既有版本，只能以 patch 方式追加。  
> 目的：封存「GitHub Required status checks 已完成」的證據，形成治理閉環的最終審計錨點。

---

## 1) 完成宣告（Operator Attestation）

- 完成日期（Asia/Taipei）：`YYYY-MM-DD HH:MM`
- 操作者：`williamhsu`
- Repo：`<owner>/<repo>`
- 受保護分支：`main` / `master`（擇一，填入實際值）
- 啟用機制：Rulesets / Branch protection rules（擇一，填入實際值）

---

## 2) Required status checks（必填證據）

### 2.1 Required check 名稱（必填）
- Workflow：`PROJECT_BOARD Gate`
- Job：`board-gate`
- GitHub UI 顯示的 check 名稱（貼上原文）：`________________________`

### 2.2 設定頁面截圖/證據（擇一即可，建議截圖）
- 證據型態：截圖 / 文字紀錄
- 內容（貼上）：  
  - `（貼上截圖檔名或文字紀錄）`

---

## 3) 行為驗證（必填：至少完成一次）

以下任一驗證成立即可（建議做 A + B）：

### A) PR 驗證（建議）
- 建立 PR → 未通過 `PROJECT_BOARD Gate / board-gate` 時 GitHub 阻擋 merge（Yes/No）
- 通過後才允許 merge（Yes/No）
- 相關 PR 連結（不貼網址也可，只貼 PR 編號）：`#____`

### B) Drift 阻擋驗證（建議）
- 人為造成 board drift（未 commit）→ CI 失敗並提示先 refresh+commit（Yes/No）
- 相關 run 證據（run id / 時間戳）：`__________`

---

## 4) 憲法級最終結論（自動成立）

只要本補丁 1~3 節證據填齊並封存，即視為：
- PROJECT_BOARD 治理閉環完成（本機 hooks + push gate + CI required checks + repair）
- 後續任何視窗不得再耗回合除錯 PROJECT_BOARD
- 若 gate FAIL：唯一合法路徑＝照 v1/v1.1/v1.2 SOP refresh/repair → commit → push

