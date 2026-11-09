# public-access-limits Specification

## Purpose
避免公開網址被單一或分散的來源濫用，造成 Bedrock 費用暴增或服務變慢，同時讓被限制的使用者知道原因：nginx 依來源 IP 限流並只轉發白名單內的公開 API，後端再設全域每日提問上限。

## Requirements

### Requirement: 提問端點限流
nginx SHALL 依來源 IP 限制 `/api/ask` 的速率，額度內立即轉發（`nodelay`），並限制每個 IP 的同時連線數。數值 SHALL 由環境變數設定：`ASK_RATE_PER_MINUTE`（預設 10）、`ASK_RATE_BURST`（預設 5）、`MAX_CONNECTIONS_PER_IP`（預設 20）。超過限制 MUST 回傳 HTTP 429，MUST NOT 轉發到後端。變數值不合法時 nginx MUST 啟動失敗。

#### Scenario: 連續提問
- **WHEN** 同一個 IP 連續送出 20 次 `POST /api/ask`
- **THEN** 前 6 次轉發到後端，其餘 14 次收到 HTTP 429，後端只收到 6 個請求

#### Scenario: 以變數調整限流
- **WHEN** `ASK_RATE_BURST=2`，同一個 IP 連續送出 10 次 `POST /api/ask`
- **THEN** 前 3 次轉發到後端，其餘 7 次收到 HTTP 429

#### Scenario: 變數不合法
- **WHEN** `ASK_RATE_PER_MINUTE` 為 0 或非數字
- **THEN** nginx 啟動失敗

#### Scenario: 不同 IP 互不影響
- **WHEN** IP A 已被限流時，IP B 送出第一次提問
- **THEN** IP B 的請求轉發到後端

### Requirement: 429 回應合約
HTTP 429 的 body SHALL 為 JSON 且與既有回應同形（`status=error`、`sql=null`、空的 `columns`／`rows`、`error_kind=null`、`refusal_source=null`），`message` 說明原因，並 SHALL 附 `Retry-After` header。

#### Scenario: 限流回應
- **WHEN** 請求被 nginx 限流
- **THEN** 回 HTTP 429、`Content-Type: application/json`、`Retry-After: 60`，`message` 為「請求太頻繁，請稍後再試」

### Requirement: 全域每日提問上限
後端 SHALL 在呼叫 Guardrail 之前檢查當日（台北時間）已處理的提問數。達到 `DAILY_QUESTION_LIMIT`（預設 500）後 MUST 回傳 HTTP 429、`message` 為「今日提問次數已達上限，請明天再試」、`Retry-After` 為距離台北午夜的秒數，MUST NOT 呼叫 Guardrail 或模型，並 SHALL 記錄 WARNING log。不合法的問題（422）MUST NOT 計入；拒答、反問與錯誤 SHALL 計入。`DAILY_QUESTION_LIMIT` 不是正整數時，服務 MUST 啟動失敗。

#### Scenario: 達到上限
- **WHEN** `DAILY_QUESTION_LIMIT=3`，當日已處理 3 個問題後再提問
- **THEN** 回 HTTP 429，Guardrail 與模型都沒有被呼叫

#### Scenario: 不合法的問題不計入
- **WHEN** `DAILY_QUESTION_LIMIT=1`，先送出空白問題（422）再送出正常問題
- **THEN** 正常問題照常處理

#### Scenario: 跨日重置
- **WHEN** 已達上限後，台北時間進入隔天
- **THEN** 計數歸零，可以正常提問

#### Scenario: 設定錯誤
- **WHEN** `DAILY_QUESTION_LIMIT` 為 0、負數或非數字
- **THEN** 服務啟動失敗並指出設定錯誤

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

#### Scenario: 公開 API 與前端照常運作
- **WHEN** 從公開網址送出 `POST /api/ask`，或請求 `/` 與前端路由
- **THEN** 提問轉給 backend 並套用限流；前端頁面由 nginx 回傳
