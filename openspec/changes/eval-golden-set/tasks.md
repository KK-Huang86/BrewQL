## 1. 用量回報

- [x] 1.1 以真實 ApplyGuardrail 確認回應 `usage` 的計費欄位；驗證：記錄欄位名稱與一次回應的數值
  - 結果（2026-11-08，guardrail version 1）：`usage` 依政策分開計 units：`topicPolicyUnits`（denied topic）、`contentPolicyUnits`（content filter，含 PROMPT_ATTACK），其餘政策（word、PII、grounding、automated reasoning、image）都是 0。10 字與 15 字的問題各為 topic 1、content 1；1,500 字為 topic 2、content 2（1 unit = 最多 1,000 字元）。通過與擋下的計費相同
- [x] 1.2 測試 + 實作：產生器回傳每次呼叫的 token 與模型 ID；輸入 Guardrail 回傳計費 units；驗證：測試由紅轉綠
- [x] 1.3 測試 + 實作：流程累計 token（含多次嘗試）、Guardrail units 與耗時，放在 `AskResult.usage`，`/api/ask` 不回傳；驗證：測試由紅轉綠
- [x] 1.4 測試 + 實作：價目表與成本計算（模型 token、Guardrail units、未知模型）；驗證：測試由紅轉綠

## 2. 測試集

- [x] 2.1 測試 + 實作：測試集載入與驗證（題號重複、欄位不完整、同時有 SQL 與預期狀態、難度不合法）；驗證：測試由紅轉綠
- [x] 2.2 撰寫 15 題黃金測試集（easy 5、medium 4、hard 2、refuse／clarify 4，含一題 prompt injection）；驗證：試跑模式下所有參考 SQL 可執行
  - 結果（2026-11-08）：`backend/evaluation/golden.yaml` 15 題（easy 5、medium 4、hard 2、refuse 4：刪除、預測、prompt injection、模糊問題反問）。試跑模式在 4.1 才完成，先以 `genbi_reader` 經 SQL 防護直接執行 11 題參考 SQL，全部可執行、結果合理（例如 q01=160、q07=76、q08=板橋區）；4.1 完成後再以試跑模式確認一次
  - 題目寫法：一般題寫明要回傳的欄位（比對以值為準，多一欄就錯）；避開有並列的「前 N 名」（評分、評論數都有並列）

## 3. 比對與指標

- [ ] 3.1 測試 + 實作：結果比較（寫法不同、列順序、需比對順序、欄位順序與名稱、浮點、日期、空結果、status 非 ok、拒答來源）；驗證：測試由紅轉綠
- [ ] 3.2 測試 + 實作：指標計算（正確率依難度、拒答正確率、p50/p95、平均 token、成本、修正次數分布、空資料）；驗證：測試由紅轉綠

## 4. 執行與報告

- [ ] 4.1 測試 + 實作：評估執行（顯示題數與預估呼叫次數、部分題目、試跑、單題錯誤不中斷），以假流程測試；驗證：測試由紅轉綠
- [ ] 4.2 測試 + 實作：JSON 與 Markdown 報告輸出；驗證：以假資料產生的報告含所有指標與明細
- [ ] 4.3 建立評估紀錄文件（每列：日期、模型、設定、題數、正確率、p95、每題成本、備註）；驗證：文件存在且格式說明清楚

## 5. 基準

- [ ] 5.1 以真實 Bedrock（Haiku 4.5、Guardrail 開啟、無 RAG）跑完整評估；驗證：報告產生，結果記入評估紀錄作為基準，並列出答錯的題目
