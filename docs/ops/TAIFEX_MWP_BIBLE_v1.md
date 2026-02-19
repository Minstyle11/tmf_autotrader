# TAIFEX MWP（一定範圍市價 / Range Market）— OFFICIAL Ops Bible v1

## 1) 名詞對齊（交易所 vs Shioaji）
- TAIFEX：「一定範圍市價單」（俗稱 MWP / Market with Protection）
- Shioaji：`price_type=MKP`（Range Market）=> 視為 MWP 的等價語意

## 2) 交易所定義的核心（必須按此建模）
- 一定範圍不是固定點數；通常是「基準價 * 百分比」計算而得。
- 例：指數期貨 TX（日盤）單式委託一定範圍 = 前一日標的收盤指數 * 0.5%
- 夜盤基準改用「最近之標的收盤指數」（同樣以百分比計算）
- tick rounding：買方轉換價 = 最佳買價 + 一定範圍（向上進位到 tick）；賣方轉換價 = 最佳賣價 - 一定範圍（向下捨去到 tick）

## 3) 系統落地要求（OrderGuard / Execution）
- 當策略意圖為「市價」時，執行層應優先用 `MKP`（Range Market）來代表 MWP，而非理想化 `MKT`。
- 若無法取得基準價（prev_close / recent_close），不得假裝可送 MWP；要可被 policy 硬擋或降級（依 v18.x policy）。
