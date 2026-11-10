## MODIFIED Requirements

### Requirement: JSON 格式 log
應用程式 log SHALL 以每行一個 JSON 物件輸出，至少包含 `time`、`level`、`logger`、`message`，以及該事件的結構化欄位（例如 `latency_ms`、`input_tokens`、`reasons`）。log MUST NOT 包含問題原文、AWS 憑證、Grafana token 或資料庫密碼；唯一的例外是 `event` 為 `ask_audit` 的稽核 log（`audit-log`），它 SHALL 包含問題原文與 SQL。無法序列化的欄位值 SHALL 轉成字串，不得讓記錄 log 失敗。nginx 的 access log SHALL 同樣以 JSON 輸出，包含來源 IP、method、不含 query string 的路徑、狀態碼與耗時，MUST NOT 包含 request body。

#### Scenario: Guardrail 檢查
- **WHEN** 一個問題經過輸入檢查
- **THEN** 標準輸出有一行可被 JSON 解析的 log，含 `blocked`、`reasons`、`latency_ms`，且不含問題原文

#### Scenario: 稽核 log 是唯一例外
- **WHEN** 一個問題完成回答
- **THEN** 含問題原文的 log 只有 `event` 為 `ask_audit` 的那一行

#### Scenario: nginx 限流
- **WHEN** 一個請求被 nginx 以 429 擋下
- **THEN** nginx access log 有一行可被 JSON 解析的紀錄，`status` 為 429，`uri` 不含 query string
