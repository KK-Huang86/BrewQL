## Purpose

避免公開網址被單一或分散的來源濫用，造成 Bedrock 費用暴增或服務變慢，同時讓被限制的使用者知道原因。

## ADDED Requirements

### Requirement: 依端點成本分級限流
nginx SHALL 依來源 IP 限制請求速率：`/api/ask` 與串流端點每分鐘 10 次（burst 5），`/api/sql` 每分鐘 30 次（burst 10），其他 `/api/` 每分鐘 60 次（burst 20）。每個 IP 的同時連線數 SHALL 不超過 20，串流端點 SHALL 不超過 2。超過限制 MUST 回傳 HTTP 429，MUST NOT 轉發到後端。

#### Scenario: 連續提問
- **WHEN** 同一個 IP 在一分鐘內送出 20 次 `/api/ask`
- **THEN** 超過額度的請求收到 HTTP 429，後端沒有收到這些請求

#### Scenario: 不同 IP 互不影響
- **WHEN** IP A 被限流時，IP B 送出第一次提問
- **THEN** IP B 正常得到回答

### Requirement: 429 回應合約
HTTP 429 的 body SHALL 與既有回應同形（`status=error`、`sql=null`、空的 `columns`／`rows`、`error_kind=null`、`refusal_source=null`），`message` 說明原因，並 SHALL 附 `Retry-After` header。

#### Scenario: 限流回應
- **WHEN** 請求被 nginx 限流
- **THEN** 回 HTTP 429、`Retry-After`，`message` 為「請求太頻繁，請稍後再試」

### Requirement: 全域每日提問上限
後端 SHALL 在呼叫 Guardrail 之前檢查當日（UTC）已處理的提問數。超過設定的 `DAILY_QUESTION_LIMIT`（預設 500）時 MUST 回傳 HTTP 429、`message` 為「今日提問次數已達上限，請明天再試」，MUST NOT 呼叫 Guardrail 或模型。不合法的問題（422）MUST NOT 計入。觸發上限 SHALL 記錄 log 並增加指標。

#### Scenario: 達到上限
- **WHEN** 當日已處理 500 個問題後再提問
- **THEN** 回 HTTP 429，Guardrail 與模型都沒有被呼叫

#### Scenario: 跨日重置
- **WHEN** UTC 日期改變
- **THEN** 計數歸零，可以正常提問

### Requirement: 請求大小與逾時
nginx SHALL 拒絕超過 16 KB 的請求 body（HTTP 413），並 SHALL 在 10 秒內未收到完整 header 或 body 時關閉連線。

#### Scenario: 超大請求
- **WHEN** 送出 1 MB 的 `/api/ask` body
- **THEN** 回 HTTP 413，後端沒有收到

### Requirement: 內部端點不對外
nginx MUST 以白名單轉發：只有明確列出的公開 API 路徑會轉給 backend，其餘路徑 MUST NOT 轉發。`/metrics`、`/health`、`/docs`、`/openapi.json` 與管理用途端點（例如 `/api/audit`）MUST NOT 能從公開網址存取。

#### Scenario: 請求內部端點
- **WHEN** 從公開網址請求 `/metrics`、`/health`、`/docs`、`/openapi.json` 或 `/api/audit`
- **THEN** 每個都回 404，後端沒有收到請求

#### Scenario: 請求不在白名單的 API
- **WHEN** 從公開網址請求 `/api/anything-new`
- **THEN** 回 404，後端沒有收到請求

#### Scenario: 公開 API 照常運作
- **WHEN** 從公開網址送出 `POST /api/ask`
- **THEN** 請求轉給 backend 並套用限流
