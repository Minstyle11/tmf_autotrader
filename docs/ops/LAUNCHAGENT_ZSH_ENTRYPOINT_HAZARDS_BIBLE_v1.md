# LaunchAgent zsh 入口點風險治理 Bible v1

- generated_at: 2026-02-01T11:40:42+08:00
- scope: LaunchAgents 以 zsh(/bin/zsh) -c/-lc 作為 ProgramArguments 的 entrypoints
- intent: **只做稽核結論與規範落盤**；不修改既有排程/既有 LaunchAgent（尤其不可觸碰 capture chain）

## 0) 絕對原則（OFFICIAL-LOCKED 兼容）
1) 既有 LaunchAgents/排程/錄製鏈路不動；若要改善，只能 **新增獨立 LaunchAgent/獨立腳本**，並以 SHA256 sidecar 封存。
2) 任何「互動 shell 才成立」的假設都視為風險來源（LaunchAgent = 非互動、不同環境、不同 expand 規則）。
3) 任何事件真相以落盤檔案/DB events 為準（call success ≠ 事實成立）。

## 1) 為什麼 zsh entrypoints 特別容易爆
- **glob / bracket pattern**：zsh 預設 `nomatch`，像 `echo [RECOVER]` 會被當成 pattern，沒 match 就直接報 `no matches found`。
- **tilde / $HOME / source**：在 LaunchAgent 的非互動環境下，`~/`、`source ~/.xxx`、依賴 profile/rc 的寫法更容易不一致。
- **$(whoami) / command substitution**：增加不可重現性與 quoting 風險，且 Debug 時常與實際執行帳號/權限狀態混淆。

## 2) 強制規範（未來新增 LaunchAgent 一律遵守）
### 2.1 命令字串（ProgramArguments 第三段）
- 一律使用 **絕對路徑**（例如 `/Users/williamhsu/...` 或 `$HOME/...`），避免 `~/`。
- 禁用 `$(whoami)`；若必須動態使用使用者，改用 `$HOME` 或在腳本內解析。
- 避免 `;` 串接多段命令；必要時改成呼叫一個 wrapper script，並在 script 內做 `set -euo pipefail`（bash）或等價嚴格模式（zsh）。
- 禁用未引用的 `[]`、`*`、`?` 等 glob 字元；要輸出含 `[]` 的文字，必須引用：`echo '[RECOVER]'`。

### 2.2 環境載入
- 不用 `source ~/.xxx` 依賴互動 rc；改用明確檔案：例如 `source $HOME/.daytrader.env` 且確保檔案存在與權限。
- 所有 secrets/keys 只從專案指定的 secrets 檔載入（例如 `configs/secrets/*.env`），避免散落在 shell profile。

### 2.3 Shell 選型
- 若不需要 zsh 特性，優先用 `/bin/bash -lc` 取得較一致的 POSIX 行為。
- 若必須用 zsh，wrapper script 建議在最前面加上：
  - `set -euo pipefail`（注意：zsh 的 pipefail 需要 `set -o pipefail`）
  - `setopt NO_NOMATCH`（避免 no matches found 直接炸掉；或改成全面禁止 glob）

## 3) 已觀測到的風險摘要（evidence）
### 3.1 RISK_SUMMARY 原文
```
# LaunchAgents zsh risk summary (evidence from LAUNCHAGENT_ZSH_CMD_AUDIT.md)
- generated_at: 2026-02-01 11:39:30 
- total_zsh_entries: 24

## Risk counters
- ACTIVE_OR_MISC: 1  — Active agent (non-disabled) — highest impact if it breaks
- BAD_/Users/Users_PATH: 1  — Duplicated path (/Users/.../Users/...) — likely wrong absolute path
- HAS_CMD_SUBST: 4  — Command substitution in plist — reproducibility & quoting risk
- HAS_TILDE: 5  — Tilde expansion depends on shell context — LaunchAgent may differ
- USES_SOURCE: 3  — source relies on interactive shell assumptions — consider explicit env file loading
- HAS_SEMI: 3  — Multiple commands chained with ';' — easier to break quoting/state
- HAS_GLOB: 0  — Potential glob expansion — zsh strictness can break (no matches found)
- HAS_BRACE: 0  — Brace expansion — zsh-specific behavior can surprise

## Details
### ACTIVE_OR_MISC
- rationale: Active agent (non-disabled) — highest impact if it breaks
- ~Library/LaunchAgents/com.node.HIPKILocalServer.cht.plist  | state=ACTIVE_OR_MISC | flags=HAS_TILDE
```
~/Library/HiPKILocalSignServer/runHIPKILocalServer.sh
$HOME/Library/HiPKILocalSignServer/runHIPKILocalServer.sh
```

### BAD_/Users/Users_PATH
- rationale: Duplicated path (/Users/.../Users/...) — likely wrong absolute path
- ~Library/LaunchAgents/com.daytrader.pipeline.daily.plist.bak.20251031_135356  | state=DISABLED | flags=DUP_USER_PATH
```
/Users/williamhsu/Users/williamhsu/daytrader/scripts/daily_wrap.sh
```

### HAS_CMD_SUBST
- rationale: Command substitution in plist — reproducibility & quoting risk
- ~Library/LaunchAgents/_disabled/com.daytrader.quotes_fetch_daily.plist  | state=DISABLED | flags=HAS_CMD_SUBST,USES_/Users/$(whoami)
```
cd /Users/$(whoami)/daytrader/backend && ./venv/bin/python scripts/quotes_fetch_daily.py
cd $HOME/daytrader/backend && ./venv/bin/python scripts/quotes_fetch_daily.py
```
- ~Library/LaunchAgents/_disabled/com.daytrader.turnover_rank_daily.plist  | state=DISABLED | flags=HAS_CMD_SUBST,USES_/Users/$(whoami)
```
cd /Users/$(whoami)/daytrader/backend && ./venv/bin/python scripts/turnover_ranker.py && ./venv/bin/python scripts/sim_order_engine.py && ./venv/bin/python scripts/daily_review_report.py
cd $HOME/daytrader/backend && ./venv/bin/python scripts/turnover_ranker.py && ./venv/bin/python scripts/sim_order_engine.py && ./venv/bin/python scripts/daily_review_report.py
```
- ~Library/LaunchAgents/com.daytrader.reportend.plist.bak.20251031_000712  | state=DISABLED | flags=HAS_CMD_SUBST,USES_/Users/$(whoami)
```
/Users/$(whoami)/daytrader/scripts/report_end_wrap.sh
$HOME/daytrader/scripts/report_end_wrap.sh
```
- ~Library/LaunchAgents/com.daytrader.reportend.plist.bak.20251031_000836  | state=DISABLED | flags=HAS_CMD_SUBST,USES_/Users/$(whoami)
```
/Users/$(whoami)/daytrader/scripts/report_end_wrap.sh
$HOME/daytrader/scripts/report_end_wrap.sh
```

### HAS_TILDE
- rationale: Tilde expansion depends on shell context — LaunchAgent may differ
- ~Library/LaunchAgents/com.node.HIPKILocalServer.cht.plist  | state=ACTIVE_OR_MISC | flags=HAS_TILDE
```
~/Library/HiPKILocalSignServer/runHIPKILocalServer.sh
$HOME/Library/HiPKILocalSignServer/runHIPKILocalServer.sh
```
- ~Library/LaunchAgents/_disabled/com.daytrader.quotes_poller.at0846.plist  | state=DISABLED | flags=HAS_TILDE,USES_SOURCE,HAS_SEMI
```
source ~/.daytrader.env; cd /Users/williamhsu/daytrader/backend && ./venv/bin/python scripts/quotes_poller.py
source $HOME/.daytrader.env; cd /Users/williamhsu/daytrader/backend && ./venv/bin/python scripts/quotes_poller.py
```
- ~Library/LaunchAgents/_disabled/com.daytrader.shares_refresher.daily.plist  | state=DISABLED | flags=HAS_TILDE,USES_SOURCE,HAS_SEMI
```
source ~/.daytrader.env; cd /Users/williamhsu/daytrader/backend && ./venv/bin/python scripts/shares_refresher.py
source $HOME/.daytrader.env; cd /Users/williamhsu/daytrader/backend && ./venv/bin/python scripts/shares_refresher.py
```
- ~Library/LaunchAgents/_disabled/com.daytrader.universe_refresher.daily.plist  | state=DISABLED | flags=HAS_TILDE,USES_SOURCE,HAS_SEMI
```
source ~/.daytrader.env; cd /Users/williamhsu/daytrader/backend && ./venv/bin/python scripts/universe_refresher.py
source $HOME/.daytrader.env; cd /Users/williamhsu/daytrader/backend && ./venv/bin/python scripts/universe_refresher.py
```
- ~Library/LaunchAgents/_disabled/com.daytrader.shares_then_ranker.daily.plist  | state=DISABLED | flags=HAS_TILDE,CD_TILDE
```
cd ~/daytrader/backend && ./venv/bin/python scripts/shares_refresher.py && ./venv/bin/python scripts/turnover_ranker.py
cd "$HOME"/daytrader/backend && ./venv/bin/python scripts/shares_refresher.py && ./venv/bin/python scripts/turnover_ranker.py
```

### USES_SOURCE
- rationale: source relies on interactive shell assumptions — consider explicit env file loading
- ~Library/LaunchAgents/_disabled/com.daytrader.quotes_poller.at0846.plist  | state=DISABLED | flags=HAS_TILDE,USES_SOURCE,HAS_SEMI
```
source ~/.daytrader.env; cd /Users/williamhsu/daytrader/backend && ./venv/bin/python scripts/quotes_poller.py
source $HOME/.daytrader.env; cd /Users/williamhsu/daytrader/backend && ./venv/bin/python scripts/quotes_poller.py
```
- ~Library/LaunchAgents/_disabled/com.daytrader.shares_refresher.daily.plist  | state=DISABLED | flags=HAS_TILDE,USES_SOURCE,HAS_SEMI
```
source ~/.daytrader.env; cd /Users/williamhsu/daytrader/backend && ./venv/bin/python scripts/shares_refresher.py
source $HOME/.daytrader.env; cd /Users/williamhsu/daytrader/backend && ./venv/bin/python scripts/shares_refresher.py
```
- ~Library/LaunchAgents/_disabled/com.daytrader.universe_refresher.daily.plist  | state=DISABLED | flags=HAS_TILDE,USES_SOURCE,HAS_SEMI
```
source ~/.daytrader.env; cd /Users/williamhsu/daytrader/backend && ./venv/bin/python scripts/universe_refresher.py
source $HOME/.daytrader.env; cd /Users/williamhsu/daytrader/backend && ./venv/bin/python scripts/universe_refresher.py
```

### HAS_SEMI
- rationale: Multiple commands chained with ';' — easier to break quoting/state
- ~Library/LaunchAgents/_disabled/com.daytrader.quotes_poller.at0846.plist  | state=DISABLED | flags=HAS_TILDE,USES_SOURCE,HAS_SEMI
```
source ~/.daytrader.env; cd /Users/williamhsu/daytrader/backend && ./venv/bin/python scripts/quotes_poller.py
source $HOME/.daytrader.env; cd /Users/williamhsu/daytrader/backend && ./venv/bin/python scripts/quotes_poller.py
```
- ~Library/LaunchAgents/_disabled/com.daytrader.shares_refresher.daily.plist  | state=DISABLED | flags=HAS_TILDE,USES_SOURCE,HAS_SEMI
```
source ~/.daytrader.env; cd /Users/williamhsu/daytrader/backend && ./venv/bin/python scripts/shares_refresher.py
source $HOME/.daytrader.env; cd /Users/williamhsu/daytrader/backend && ./venv/bin/python scripts/shares_refresher.py
```
- ~Library/LaunchAgents/_disabled/com.daytrader.universe_refresher.daily.plist  | state=DISABLED | flags=HAS_TILDE,USES_SOURCE,HAS_SEMI
```
source ~/.daytrader.env; cd /Users/williamhsu/daytrader/backend && ./venv/bin/python scripts/universe_refresher.py
source $HOME/.daytrader.env; cd /Users/williamhsu/daytrader/backend && ./venv/bin/python scripts/universe_refresher.py
```
```

### 3.2 CMD_AUDIT 原文（完整可追溯）
```
# LaunchAgents zsh entrypoints audit
- generated_at: 2026-02-01 11:38:42 
- scanned: 103 files under /Users/williamhsu/Library/LaunchAgents
- zsh entries: 24

## Findings (ordered by risk)
- High risk patterns for zsh/LaunchAgent drift: `$(whoami)`, `~`, duplicated `/Users/.../Users/...`, unquoted glob/brace, multi-command `;`/`&&` chains without strict quoting.

### ~Library/LaunchAgents/com.node.HIPKILocalServer.cht.plist
- state: `ACTIVE_OR_MISC`
- zsh: `zsh -c`
- flags: `HAS_TILDE`
```
~/Library/HiPKILocalSignServer/runHIPKILocalServer.sh
```
- suggested_normalized_cmd:
```
$HOME/Library/HiPKILocalSignServer/runHIPKILocalServer.sh
```

### ~Library/LaunchAgents/_disabled/com.daytrader.quotes_poller.at0846.plist
- state: `DISABLED`
- zsh: `/bin/zsh -lc`
- flags: `HAS_TILDE,USES_SOURCE,HAS_SEMI`
```
source ~/.daytrader.env; cd /Users/williamhsu/daytrader/backend && ./venv/bin/python scripts/quotes_poller.py
```
- suggested_normalized_cmd:
```
source $HOME/.daytrader.env; cd /Users/williamhsu/daytrader/backend && ./venv/bin/python scripts/quotes_poller.py
```

### ~Library/LaunchAgents/_disabled/com.daytrader.shares_refresher.daily.plist
- state: `DISABLED`
- zsh: `/bin/zsh -lc`
- flags: `HAS_TILDE,USES_SOURCE,HAS_SEMI`
```
source ~/.daytrader.env; cd /Users/williamhsu/daytrader/backend && ./venv/bin/python scripts/shares_refresher.py
```
- suggested_normalized_cmd:
```
source $HOME/.daytrader.env; cd /Users/williamhsu/daytrader/backend && ./venv/bin/python scripts/shares_refresher.py
```

### ~Library/LaunchAgents/_disabled/com.daytrader.universe_refresher.daily.plist
- state: `DISABLED`
- zsh: `/bin/zsh -lc`
- flags: `HAS_TILDE,USES_SOURCE,HAS_SEMI`
```
source ~/.daytrader.env; cd /Users/williamhsu/daytrader/backend && ./venv/bin/python scripts/universe_refresher.py
```
- suggested_normalized_cmd:
```
source $HOME/.daytrader.env; cd /Users/williamhsu/daytrader/backend && ./venv/bin/python scripts/universe_refresher.py
```

### ~Library/LaunchAgents/_disabled/com.daytrader.quotes_fetch_daily.plist
- state: `DISABLED`
- zsh: `/bin/zsh -lc`
- flags: `HAS_CMD_SUBST,USES_/Users/$(whoami)`
```
cd /Users/$(whoami)/daytrader/backend && ./venv/bin/python scripts/quotes_fetch_daily.py
```
- suggested_normalized_cmd:
```
cd $HOME/daytrader/backend && ./venv/bin/python scripts/quotes_fetch_daily.py
```

### ~Library/LaunchAgents/_disabled/com.daytrader.shares_then_ranker.daily.plist
- state: `DISABLED`
- zsh: `/bin/zsh -lc`
- flags: `HAS_TILDE,CD_TILDE`
```
cd ~/daytrader/backend && ./venv/bin/python scripts/shares_refresher.py && ./venv/bin/python scripts/turnover_ranker.py
```
- suggested_normalized_cmd:
```
cd "$HOME"/daytrader/backend && ./venv/bin/python scripts/shares_refresher.py && ./venv/bin/python scripts/turnover_ranker.py
```

### ~Library/LaunchAgents/_disabled/com.daytrader.turnover_rank_daily.plist
- state: `DISABLED`
- zsh: `/bin/zsh -lc`
- flags: `HAS_CMD_SUBST,USES_/Users/$(whoami)`
```
cd /Users/$(whoami)/daytrader/backend && ./venv/bin/python scripts/turnover_ranker.py && ./venv/bin/python scripts/sim_order_engine.py && ./venv/bin/python scripts/daily_review_report.py
```
- suggested_normalized_cmd:
```
cd $HOME/daytrader/backend && ./venv/bin/python scripts/turnover_ranker.py && ./venv/bin/python scripts/sim_order_engine.py && ./venv/bin/python scripts/daily_review_report.py
```

### ~Library/LaunchAgents/com.daytrader.reportend.plist.bak.20251031_000712
- state: `DISABLED`
- zsh: `/bin/zsh -lc`
- flags: `HAS_CMD_SUBST,USES_/Users/$(whoami)`
```
/Users/$(whoami)/daytrader/scripts/report_end_wrap.sh
```
- suggested_normalized_cmd:
```
$HOME/daytrader/scripts/report_end_wrap.sh
```

### ~Library/LaunchAgents/com.daytrader.reportend.plist.bak.20251031_000836
- state: `DISABLED`
- zsh: `/bin/zsh -lc`
- flags: `HAS_CMD_SUBST,USES_/Users/$(whoami)`
```
/Users/$(whoami)/daytrader/scripts/report_end_wrap.sh
```
- suggested_normalized_cmd:
```
$HOME/daytrader/scripts/report_end_wrap.sh
```

### ~Library/LaunchAgents/com.daytrader.capture_hot20_preopen_check.plist.disabled_20251222_213835
- state: `DISABLED`
- zsh: `/bin/zsh -lc`
- flags: `USES_HOME_OK`
```
cd "$HOME/daytrader" && ./scripts/capture_hot20_preopen_check.sh
```

### ~Library/LaunchAgents/com.daytrader.capture_hot20_status_0915.plist.disabled_20251222_213835
- state: `DISABLED`
- zsh: `/bin/zsh -lc`
- flags: `USES_HOME_OK`
```
cd "$HOME/daytrader" && ./scripts/hot20_status_0915.sh
```

### ~Library/LaunchAgents/com.daytrader.capture_hot20_status_1335.plist.disabled_20251222_213835
- state: `DISABLED`
- zsh: `/bin/zsh -lc`
- flags: `USES_HOME_OK`
```
cd "$HOME/daytrader" && ./scripts/hot20_status_1335.sh
```

### ~Library/LaunchAgents/com.daytrader.pipeline.daily.plist.bak.20251031_135356
- state: `DISABLED`
- zsh: `/bin/zsh -lc`
- flags: `DUP_USER_PATH`
```
/Users/williamhsu/Users/williamhsu/daytrader/scripts/daily_wrap.sh
```

### ~Library/LaunchAgents/_disabled/com.daytrader.heartbeat.plist
- state: `DISABLED`
- zsh: `/bin/zsh -lc`
- flags: `(none)`
```
cd /Users/williamhsu/daytrader/backend && ./venv/bin/python scripts/heartbeat_notify.py
```

### ~Library/LaunchAgents/_disabled/com.daytrader.report_end.plist
- state: `DISABLED`
- zsh: `/bin/zsh -lc`
- flags: `(none)`
```
cd "/Users/williamhsu/daytrader" && ./scripts/report_end_wrap.sh
```

### ~Library/LaunchAgents/_disabled/com.daytrader.turnover.guard.plist
- state: `DISABLED`
- zsh: `/bin/zsh -lc`
- flags: `(none)`
```
cd /Users/williamhsu/daytrader/backend && ./venv/bin/python scripts/turnover_guard.py
```

### ~Library/LaunchAgents/_disabled/com.daytrader.turnover.pipeline.plist
- state: `DISABLED`
- zsh: `/bin/zsh -lc`
- flags: `(none)`
```
cd /Users/williamhsu/daytrader/backend && bash scripts/turnover_pipeline.sh
```

### ~Library/LaunchAgents/_disabled/com.daytrader.turnover.retry.plist
- state: `DISABLED`
- zsh: `/bin/zsh -lc`
- flags: `(none)`
```
cd /Users/williamhsu/daytrader/backend && bash scripts/retry_if_bad.sh
```

### ~Library/LaunchAgents/_disabled/com.daytrader.turnover_pipeline.afternoon.plist
- state: `DISABLED`
- zsh: `/bin/zsh -lc`
- flags: `(none)`
```
cd /Users/williamhsu/daytrader/backend && ./venv/bin/python scripts/pipeline_selfcheck_run.py
```

### ~Library/LaunchAgents/_disabled/com.daytrader.turnover_pipeline.morning.plist
- state: `DISABLED`
- zsh: `/bin/zsh -lc`
- flags: `(none)`
```
cd /Users/williamhsu/daytrader/backend && ./venv/bin/python scripts/pipeline_selfcheck_run.py
```

### ~Library/LaunchAgents/com.daytrader.daily_backtest.plist.bak_20251123_135311
- state: `DISABLED`
- zsh: `/bin/zsh -lc`
- flags: `(none)`
```
/Users/williamhsu/daytrader/run_daily_backtest.sh
```

### ~Library/LaunchAgents/com.daytrader.feature_daemon.plist.bak_20251114
- state: `DISABLED`
- zsh: `/bin/zsh -lc`
- flags: `(none)`
```
/Users/williamhsu/daytrader/backend/venv/bin/python -u /Users/williamhsu/daytrader/backend/scripts/feature_daemon.py
```

### ~Library/LaunchAgents/com.daytrader.pipeline.daily.plist.bak.20251031_135120
- state: `DISABLED`
- zsh: `/bin/zsh -lc`
- flags: `(none)`
```
/Users/williamhsu/daytrader/scripts/daily_wrap.sh
```

### ~Library/LaunchAgents/com.daytrader.snapshot-loop.plist.bak.132739
- state: `DISABLED`
- zsh: `/bin/zsh -lc`
- flags: `(none)`
```
/Users/williamhsu/daytrader/bin/snapshot-loop-run
```
```

