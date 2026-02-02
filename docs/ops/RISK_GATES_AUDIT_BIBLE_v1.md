# RISK_GATES_AUDIT_BIBLE_v1 (TMF AutoTrader)

## 目的
把「紙上交易 Paper OMS」在下單前的風控閘門（Risk Gates）做到：
1) 每一筆下單（PASS/REJECT）都可追溯（audit-ready）  
2) DB `orders.meta_json` 永遠保留呼叫端 meta + `risk_verdict`  
3) REJECT 也要寫入 `orders`（status=REJECTED）  
4) PASS 也要把 `risk_verdict(ok=True, code=OK, ...)` 一起存進 `orders.meta_json`

## 關鍵設計
### 1) REJECT path：PaperOMSRiskWrapperV1._insert_rejected_order()
- 一定 INSERT 一筆 `orders`
- `meta_json` 必須是「呼叫端 meta + risk_verdict」的 merge 後結果
- 回傳 dict（給上層流程快速判斷），同時 DB 留存完整 meta

### 2) PASS path：PaperOMSRiskWrapperV1.place_order()
- `risk.check_pre_trade(...)` 通過後：
  - 產生 `meta_ok = caller_meta + risk_verdict(ok=True, code='OK', ...)`
  - **用 meta_ok 呼叫 PaperOMS.place_order(...)**
- 之後 PaperOMS.match() 會 UPDATE `orders`：
  - status -> FILLED / PARTIALLY_FILLED
  - meta_json merge `filled_qty`（不可覆蓋原本 meta 欄位）

### 3) PaperOMS._upd_order_status()
- 先 SELECT 原本 `meta_json` -> base(dict)
- base["filled_qty"]=...
- UPDATE 時寫回 `_j(base)`，確保 stop_price / market_metrics / risk_verdict 等都不會消失

## DB 應該長什麼樣子（驗收標準）
對任一筆 `orders`：
- PASS + FILLED：
  - meta_keys 至少包含：ref_price, stop_price, market_metrics, risk_verdict, filled_qty
  - risk_verdict.ok=True 且 code='OK'
- REJECT：
  - meta_keys 至少包含：risk_verdict
  - 若呼叫端有 market_metrics/ref_price/stop_price，必須保留（不能被覆蓋/丟失）
  - risk_verdict.ok=False 且 code 為實際拒單原因（例如 RISK_STOP_REQUIRED）

## 風控閘門 smoke tests（src/risk/run_risk_gates_smoke_v1.py）
必須涵蓋並 PASS：
- RISK_STOP_REQUIRED
- RISK_MARKET_METRICS_REQUIRED
- RISK_PER_TRADE_MAX_LOSS
- RISK_DAILY_MAX_LOSS
- RISK_CONSEC_LOSS_COOLDOWN

並且：
- seed trades 必須在腳本結束時清乾淨（DB 不污染）
- 檢查 seed_count=0、today_realized_pnl=0 為預期

## 驗收步驟（逐步） / Acceptance Steps
### A. 風控閘門 smoke test
1) 執行：
   - `python3 src/risk/run_risk_gates_smoke_v1.py`
2) 預期：
   - 每個 [TEST] ... -> PASS
   - 最後印出 `[OK] all risk gate smoke tests PASS`
3) 清理確認（同一支腳本或額外檢查）：
   - seed_any=0
   - today_realized_pnl=0.0

### B. Paper live smoke（src/oms/run_paper_live_v1.py）
1) 執行：
   - `python3 src/oms/run_paper_live_v1.py`
2) 預期：
   - case1_stop_missing -> REJECTED (RISK_STOP_REQUIRED)
   - case2 -> PASS 下單 + match 產生 fills=1 + order status=FILLED

### C. DB audit（orders.meta_json）
1) 查最近 8 筆 orders：
   - 確認 PASS/FILLED 與 REJECT 的 meta_json 皆符合「驗收標準」
2) 核心點：
   - PASS/FILLED 仍保有 risk_verdict、market_metrics、stop_price
   - REJECT 仍保有呼叫端 meta（若有）+ risk_verdict


## Audit quick-check (last200) — 2026-01-31T11:10:42
- db: runtime/data/tmf_autotrader_v1.sqlite3
- checked_orders: 89
- anomalies_missing_risk_verdict: 0

✅ No anomalies in last200 (all orders have risk_verdict)

### Latest risk codes (top 12)
- id=89 status=FILLED code=OK ok=True
- id=88 status=REJECTED code=RISK_STOP_REQUIRED ok=False
- id=87 status=REJECTED code=RISK_CONSEC_LOSS_COOLDOWN ok=False
- id=86 status=REJECTED code=RISK_DAILY_MAX_LOSS ok=False
- id=85 status=REJECTED code=RISK_PER_TRADE_MAX_LOSS ok=False
- id=84 status=REJECTED code=RISK_MARKET_METRICS_REQUIRED ok=False
- id=83 status=REJECTED code=RISK_STOP_REQUIRED ok=False
- id=82 status=FILLED code=OK ok=True
- id=81 status=REJECTED code=RISK_STOP_REQUIRED ok=False
- id=80 status=REJECTED code=RISK_CONSEC_LOSS_COOLDOWN ok=False
- id=79 status=REJECTED code=RISK_DAILY_MAX_LOSS ok=False
- id=78 status=REJECTED code=RISK_PER_TRADE_MAX_LOSS ok=False
