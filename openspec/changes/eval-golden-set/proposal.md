## Why

「正確率幾 %、每題多少錢、哪裡會錯」是這個專案和一般「跟資料庫聊天」Demo 最大的差別。評估要盡早建立：之後每個改動（更多資料、RAG、換模型）都要能用同一套題目證明「變好了」，而不是憑感覺。

## What Changes

- 黃金測試集：15 題（簡單、中等、困難、應拒答或反問），每題有參考 SQL 或預期狀態
- 一鍵評估：對每題跑完整流程，用「比對查詢結果」判斷對錯（不比對 SQL 字串）
- 指標：整體與各難度正確率、拒答正確率、p50／p95 回應時間、平均 token 與每題成本、修正次數分布
- 報告：每次執行輸出 JSON 與 Markdown；重要的結果手動記入版本控制中的評估紀錄
- 流程回報 token 與 Guardrail 用量，供成本計算；價目表集中一處，之後監控沿用

## Capabilities

### New Capabilities

- `evaluation`: 黃金測試集、評估執行、結果比對、指標與報告。

### Modified Capabilities

- `query-pipeline`: 回報每個問題的 token、Guardrail 用量與耗時。
- `input-guardrails`: 檢查結果帶回 ApplyGuardrail 的計費 units。

## Impact

- 新增：黃金測試集檔案、評估執行程式、評估紀錄文件
- 修改：流程、產生器與輸入 Guardrail 回傳用量；新增價目表
- 成本：每次完整評估約 15～45 次模型呼叫；以 Haiku 計約數美分
- 依賴 ticket：`refuse-and-clarify`、`self-correct-on-error`
