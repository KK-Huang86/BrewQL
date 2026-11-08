# 評估紀錄

這裡記錄重要的評估結果，例如基準線、RAG 前後、模型比較。每次執行的完整報告在 `backend/evaluation/reports/`，不進版控；這份文件是人工整理的摘要，也是面試時引用數據的來源。

## 怎麼跑

```bash
# 只檢查參考 SQL，不呼叫模型（免費）
uv --directory backend run python -m evaluation --dry-run

# 完整評估（會呼叫 Bedrock 與 Guardrail，15 題約 US$0.03）
uv --directory backend run python -m evaluation
```

需要和 API 相同的設定：AWS 憑證、`BEDROCK_*`，以及以 `genbi_reader` 連線的 `DATABASE_URL`。

## 怎麼記

一次執行記一列。欄位：

| 欄位 | 內容 |
|---|---|
| 日期 | 執行日期（UTC） |
| 模型 | Bedrock 模型 ID |
| 設定 | 會影響結果的設定，例如 Guardrail 版本、`MAX_SQL_RETRIES`、有沒有 RAG、prompt 改動 |
| 題數 | 這次跑了幾題 |
| 正確率 | 答對題數／總題數，並列出 easy／medium／hard／refuse 各自的結果 |
| p95 | 回應時間 p95 |
| 每題成本 | 平均每題美元，包含模型 token 與 Guardrail |
| 備註 | 答錯的題號與原因、和上一列比較的結論 |

規則：

- 只記錄值得比較的執行，不是每次都要記。
- 比較兩次執行時，除了要比較的那一項，其他設定要相同；不同時寫在備註。
- 模型輸出不是固定的，重要的比較要跑 2 次，取平均或兩次都記。
- 題目有增減時，在備註註明，正確率不能直接和舊的比較。

## 紀錄

| 日期 | 模型 | 設定 | 題數 | 正確率 | p95 | 每題成本 | 備註 |
|---|---|---|---|---|---|---|---|
| 2026-11-07 | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | 基準線：Guardrail v1、`MAX_SQL_RETRIES=1`、無 RAG、資料只有 `cafes` | 15 | 14/15（easy 5/5、medium 3/4、hard 2/2、refuse 4/4） | 2,607 ms | $0.0017 | 誤擋 1 題：q09（2025 年每月新上架）被模型以「無法預測未來」拒答，模型不知道今天的日期，把 2025 年當成未來。q14 prompt injection 由輸入 Guardrail 擋下（0 次模型呼叫）。沒有題目觸發重試。總成本 $0.0257 |
| 2026-11-07 | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | 同基準線，system prompt 加上今天日期（台北時間）與歷史資料說明 | 15 | 15/15（easy 5/5、medium 4/4、hard 2/2、refuse 4/4），連跑 2 次相同 | 2,564 ms／2,928 ms | $0.0018 | q09 修正：2025 年被當成歷史資料查詢。q13「預測下個月」仍正確拒答，日期說明沒有讓預測題被誤放行。日期說明讓每題輸入多約 60 token（約 +$0.0001）。兩次總成本 $0.0266、$0.0266 |
