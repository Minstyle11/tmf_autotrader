# PROJECT_BOARD Governance Bible v1 (OFFICIAL-LOCKED)
**ts**: 2026-02-06T08:42:12
**scope**: TMF AutoTrader (all windows, until project completion)

## Non-negotiable Rules
1) Single Source of Truth (canonical): docs/board/PROJECT_BOARD.md

Example absolute path (this machine): /Users/williamhsu/tmf_autotrader/docs/board/PROJECT_BOARD.md
2) Status Legend is canonical and must be auto-synced:
   - [ ] TODO
   - [~] DOING
   - [x] DONE
   - [!] BLOCKED
3) Board work-items must remain aligned with v18 + v18.x (bibles) and must be completed.
4) Any window handoff must include board + refresh/update scripts + BIBLES_INDEX_v18x.json.
5) Do not manually edit progress header numbers; always run pm_refresh_board.sh/v2.py.

## Operational Entry Points
- scripts/pm_refresh_board.sh
- scripts/pm_refresh_board_v2.py
- scripts/m6_update_project_board_v1.sh
- src/ops/board_mark_doing_v1.py
- docs/board/BIBLES_INDEX_v18x.json
