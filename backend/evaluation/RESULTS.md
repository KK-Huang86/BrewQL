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
