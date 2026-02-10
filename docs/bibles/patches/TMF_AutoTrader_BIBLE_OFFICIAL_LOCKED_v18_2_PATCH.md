# TMF_AutoTrader_BIBLE_OFFICIAL_LOCKED_v18.2_PATCH
> 本文件為 v18 的「補強 Patch」。主線仍以 v18 為 One-Doc/One-Truth；本 Patch 以 *增補* 與 *澄清* 為主，避免破壞既有治理。  
> 目標：把 v18 再往「機構級」推進一階：**期望值建模 → 微結構/執行 → 風險/倉位 → 選擇權/波動率 → 自主學習閉環**，並落地到 **永豐金（SinoPac）Shioaji** + **TAIFEX 規則** 的現實約束。

---

## 0) 本 Patch 依據與新增參考來源（高負載摘要）
### 0.1 官方/產業規範（需納入程式設計假設）
- **TAIFEX 動態價格穩定措施（Dynamic Price Banding Mechanism, DPBM）**：當成交模擬價超過上下限，交易所會直接拒單；策略與執行層必須能偵測/處理被拒與重新報價（含撤單/重掛/降價/退避）。citeturn0search0turn0search4turn0search12turn0search16turn0search8
- **交易所/清算風控的典型機構做法**：pre-trade credit controls、kill switch、訊息節流、稽核軌跡與事後對帳是標配。citeturn0search2turn0search6turn0search10turn0search18turn0search14

### 0.2 執行端（永豐金 Shioaji）
- Shioaji 的 **Streaming Market Data / subscribe(tick,bidask)**、quote callback、以及 quote-binding 等高階用法，必須被納入「報價中斷偵測、延遲監控、撮合保護、與策略節流」。citeturn0search1turn0search21turn0search5turn0search13

### 0.3 回測/研究誠實性（AFML/De Prado）
- **Purged Cross-Validation / Embargo** 需要進一步制度化：任何用到未來資訊形成標籤或特徵的流程，若沒有 purging/embargo，視為不合格。citeturn0search3turn0search15turn0search19turn0search11

---

## 1) 期望值（Expected Return）建模：把「策略好不好」從回測曲線拉回可驗證的來源
> 你要打造長期穩定、能大賺小賠的系統，核心不是「找到一段曲線」，而是**可解釋、可分解、可檢驗、可持續的期望值來源**。  
> v18 已有風控與治理，本 Patch 補上「期望值來源的制度化」。

### 1.1 交易型期望值的三層分解（必須在研究報告中固定輸出）
1) **結構性溢酬（structural premia）**  
   - 例：期貨的風險溢酬、流動性溢酬、波動率溢酬（若做選擇權）、槓桿與保證金帶來的行為面溢酬。  
2) **訊號溢酬（signal alpha）**  
   - 例：趨勢/動能、均值回歸、breakout、order-flow/微結構訊號、期限結構/日內季節性等。  
3) **執行溢酬（execution edge）**  
   - 例：降低衝擊成本、降低 spread crossing、把 rejection/滑價風險納入策略判斷。

> **規則**：任何策略候選，必須說清楚「它屬於哪一類期望值」，以及「如何在台指期/小台指期被驗證」。如果說不清楚 → 不進主線。

### 1.2 期望值估計的「不許偷吃」規格
- 任何估計都要報：**估計區間、樣本分布、斷點（regime shift）敏感度、與成本/滑價假設**。
- 指標最少固定輸出：CAGR（或日/週期望值）、Sharpe/Sortino、Calmar、MaxDD、尾部分位（p1/p5）、勝率、profit factor、平均持倉時間、平均/分位滑價、rejection rate。
- **多重檢定控制**：參數 sweep 不是越多越好；必須有「白紙假說」與「淘汰率」。使用 purged CV / CPCV 才能把過擬合壓下來。citeturn0search3turn0search19

---

## 2) 市場微結構（Market Microstructure）：把「價差/五檔/委託簿」納入策略與執行一體化
> v18 已有 execution / risk / kill switch，但還缺「微結構的量化語言」：  
> **bid-ask spread、order flow、informed vs. uninformed、queue priority、impact** 這些必須變成資料欄位與決策邏輯。

### 2.1 必備的「微結構資料欄位」（若 Shioaji 可得，優先用；不可得則以 proxy）
- mid price、spread（ticks & bps）、order book imbalance（L1~L5）、microprice、trade sign / aggressive side（可用 bidask+last 估）、短窗成交量/筆數、短窗 volatility、短窗撤單率/更新率（若可估）。
- 交易時間維度：開盤/收盤前後、夜盤流動性分段、結算日前後、重大公告前後（需日曆）。

### 2.2 兩個「必做」的微結構模型（先簡後繁）
1) **成本模型 v2（Slippage Model v2）**  
   - 成本 = 手續費/稅 + spread crossing + impact + latency drift + rejection re-quote cost  
   - 必須把 DPBM 拒單視為「額外成本風險」，並輸出 rejection 的條件統計。citeturn0search0turn0search12
2) **交易品質評分（Execution Quality Score）**  
   - 每筆交易輸出：是否跨價差、成交耗時、偏離 mid 的幅度、成交時 spread、成交時短窗波動、是否在流動性差時段、是否發生重掛/拒單。

> **規則**：研究回測若未計入 slippage v2（含 spread/impact/rejection proxy），視為研究不合格，不得進主線。

---

## 3) 選擇權/波動率（Options & Volatility）：用來「擴展策略宇宙」與「尾部風險治理」
> 你目前主線是期貨（台指/小台），但「波動率」是期貨交易的底層風險因素。  
> 本 Patch 的目標不是立刻做期權高頻，而是把 **波動率面** 變成策略與風控的公共資產（shared feature & shared risk layer）。

### 3.1 波動率必備觀念（要變成模組，不只是知識）
- Realized vol vs. Implied vol、skew/smile、term structure、vol-of-vol、Gamma/Vega/Theta 風險。
- **波動率目標化（Volatility Targeting）**：用波動率當 position sizing 的「共同尺度」，能把不同 regime 的曝險拉回可控範圍。

### 3.2 期貨主線的「最低限度」波動率整合（不做選擇權也要做）
- 風控層新增：  
  - `vol_regime`: 低/中/高（可用 ATR、realized vol、或交易所波動指數 proxy）  
  - `vol_spike_guard`: 當短窗 vol 爆升 → 降頻、降倉、或只允許特定策略（例如只做均值回歸、或只做突破，依你定義）
- 策略層新增：  
  - `signal_confidence` 必須被 `vol_regime` 調制（高波動時假訊號更多、滑價更大）

### 3.3 若未來要納入選擇權（先把骨架在 v18 主線留好）
- 建立 `derivatives_core`：Greeks 計算、margin 模型、scenario PnL（delta-gamma-vega）  
- 建立 `hedging_engine`：delta hedge、gamma scalping 的回測規格（含交易成本、滑價、與流動性門檻）

---

## 4) 槓桿/保證金/倉位：把「會賺」變成「活得久」
> 期貨最大的風險不是策略本身，是槓桿與尾部波動。  
> v18 已有 risk budget，本 Patch 把「槓桿-波動-回撤」的連結更制度化。

### 4.1 倉位 sizing 的兩階段門檻（Hard Gate）
1) **研究階段（paper/回測）**：只允許「固定風險單位」 sizing  
   - 每筆交易 risk = `R`（例如 0.1%~0.3% equity），用 stop distance / vol distance 去算口數  
2) **上線階段（paper live / real）**：才允許 adaptive sizing  
   - 但必須有：vol targeting、drawdown throttle、consecutive loss cooldown、與日內風險重置規則（v18 已有，這裡要求必須與 sizing 綁死）

### 4.2 Kelly / Fractional Kelly 的使用準則（避免自殺）
- Kelly 只能當「上限參考」，不可直接全額套用；必須用 **fractional Kelly**，並且用保守估計（下分位的勝率/報酬比）做輸入。  
- 如果策略是 regime-sensitive（大多數都是），Kelly 估計必須分 regime 做，且要有 shrinkage（向整體均值收縮）。

---

## 5) 執行與風控：把「交易所拒單/斷線/延遲」納入 state machine，而不是例外處理
> v18 已有 watchdog/kill switch，但這一段補上更「交易所真實世界」的規格。

### 5.1 DPBM / 交易所保護機制的必備狀態機
- `ORDER_REJECTED_DPBM`：  
  - 行為：記錄拒單原因 → 退避（exponential backoff）→ 重新評估是否仍要成交（信號是否仍有效、spread 是否擴大、vol 是否升高）→ 重新下單或取消交易  
  - **重要**：拒單不是「再下一次就好」，它通常代表市場正在劇烈移動、或你價格過度激進。citeturn0search0turn0search12

### 5.2 Shioaji 串流與斷線治理（必做）
- heartbeat/last_tick_ts 監控：超過阈值（例如 2s、5s、10s 分段） → 進入 `DATA_STALE` 狀態  
- `DATA_STALE` 狀態下禁止任何新開倉；若已有部位，執行「保守模式」：只允許減倉/平倉、並降低委託頻率。citeturn0search1turn0search21

### 5.3 機構級 pre-trade risk control 清單（必備）
- max order size、max position、max notional、max order rate、max message rate、price band sanity check、self-trade prevention（若平台支援）、kill switch。citeturn0search10turn0search6turn0search14

---

## 6) 自主學習/自我改進：把「研究→上線→回饋」變成可重播的閉環
> 你要的是「越跑越強」的系統，而不是一次性策略。

### 6.1 最小可行的自我改進（v18 主線必須內建）
- 每日自動產出：  
  1) 今日策略表現（含成本分解、rejection 統計、分時段績效）  
  2) 風控事件（cooldown、kill switch、data stale）摘要  
  3) 研究候選隊列（top-K candidates）更新：新增/淘汰理由
- 任何「自動調參」都必須在 paper 環境先跑過 **purged CV + walk-forward**，再進 canary。citeturn0search3turn0search15

---

## 7) 對 v18 的「精準修改建議」（不改也能先上線，但建議排進 v18.x 主線）
> 以下是我認為最值得立刻進主線的變更點（依 ROI 排序）：

1) **Slippage Model v2**（spread/impact/latency/rejection）成為所有回測預設成本模型  
2) **DPBM-aware execution state machine**（拒單/重掛/退避/再評估）  
3) **Vol regime** 納入策略 gating + sizing  
4) **Execution Quality Score**：讓你能用數據追責「為什麼這筆明明訊號對卻沒賺」  
5) **Pre-trade risk checklist** 落地到程式參數與 hard gates

---

## 8) 驗收步驟（逐步）
> 這份 Patch 是要讓主線視窗直接落地，所以給一份「可以照著做」的驗收流程。

### 8.1 文件驗收（5 分鐘）
1. 確認你主線視窗已載入 v18（One-Doc/One-Truth）。  
2. 上傳本 Patch（v18.2）後，主線視窗應能指出：  
   - 新增了哪些模組與狀態機  
   - 哪些是「研究必備」hard gate（如 slippage v2）  
   - 哪些是「上線必備」hard gate（如 data stale 禁止開倉、kill switch）

### 8.2 研究端驗收（半天～1 天，依你現有框架）
1. 在回測輸出中新增成本分解欄位：fee、spread、impact、latency、rejection_proxy  
2. 新增輸出：execution_quality_score（每筆交易）  
3. 對同一策略：  
   - 用舊成本模型跑一次  
   - 用 slippage v2 跑一次  
   - 確認績效差異與原因可解釋（spread/impact 是否吃掉 edge）

### 8.3 執行端驗收（paper live）
1. 在 Shioaji streaming callback 中，加入 last_tick_ts/heartbeat 監控  
2. 觸發 DATA_STALE（可用手動斷網/關閉串流測試）  
3. 驗證：DATA_STALE 時 **禁止新開倉**，只允許減倉/平倉，並有告警  
4. 模擬 DPBM 拒單（或用價格帶外下單的方式，若券商端可回報）  
5. 驗證：拒單後進入 ORDER_REJECTED_DPBM 狀態機，會退避並重新評估，而不是無腦重送

---

## 9) 後續若要再更強：我建議你「優先補」的資料/書（若你願意再提供）
> v18 已經很強，但要再往機構級推一階，最有用的是「規範與真實事故經驗」：
1) 交易所/監管的 algo trading 風控指引（CFTC / ESMA / FCA 等）  
2) 券商/交易所的 order throttling / session management / drop-copy / audit trail 文件  
3) 台灣本地：TAIFEX 更完整的規則/結算/追繳流程細節（若有中文/英文完整版本）

---

# END OF PATCH
