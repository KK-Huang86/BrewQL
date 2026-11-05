## Purpose

定義前端與後端之間的 HTTP 合約，包含健康檢查與提問。

## ADDED Requirements

### Requirement: 健康檢查
系統 SHALL 提供 `GET /health`，回傳 HTTP 200 與 `{"status": "ok"}`，且 MUST NOT 依賴資料庫或 Bedrock 是否可用。

#### Scenario: 外部依賴不可用
- **WHEN** 資料庫與 Bedrock 都無法連線時呼叫 `GET /health`
- **THEN** 仍回傳 HTTP 200 與 `{"status": "ok"}`

### Requirement: 提問端點
系統 SHALL 提供 `POST /api/ask`，請求為 `{"question": string}`（1~1000 字元），回應為 JSON，含 `status`、`sql`、`columns`、`rows`、`message`。日期 MUST 序列化為 ISO 8601 字串，Decimal MUST 序列化為 JSON 數字。

#### Scenario: 成功
- **WHEN** 送出合法問題且流程成功
- **THEN** 回傳 HTTP 200、`status=ok`

#### Scenario: 不合法輸入
- **WHEN** 缺少 `question`、為空字串或超過 1000 字元
- **THEN** 回傳 HTTP 422

#### Scenario: SQL 被拒絕
- **WHEN** 模型產生的 SQL 未通過防護
- **THEN** 回傳 HTTP 200、`status=error` 與原因

#### Scenario: Bedrock 無法使用
- **WHEN** 呼叫 Bedrock 失敗
- **THEN** 回傳 HTTP 502，回應仍含五個欄位（`status=error`、`sql=null`、空的 `columns`/`rows`、通用 `message`），錯誤追蹤只記錄一次，回應不含內部錯誤細節

#### Scenario: 資料庫無法連線
- **WHEN** 連線池無法建立（資料庫未啟動、密碼錯誤）
- **THEN** 回傳 HTTP 503 與「資料庫暫時無法使用」，不誤報為模型錯誤；下一次提問會重新嘗試連線

#### Scenario: 服務關閉
- **WHEN** API 服務關閉
- **THEN** 關閉資料庫連線池

### Requirement: CORS
系統 SHALL 只允許設定的前端來源跨域呼叫，只開放 `GET` 與 `POST`。

#### Scenario: 未授權來源
- **WHEN** 來自未設定網域的預檢請求
- **THEN** 回應不含允許該來源的 header
