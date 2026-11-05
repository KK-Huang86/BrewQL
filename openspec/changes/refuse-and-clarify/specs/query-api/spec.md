## MODIFIED Requirements

### Requirement: 提問端點
系統 SHALL 提供 `POST /api/ask`，請求為 `{"question": string}`（1~1000 字元），回應為 JSON，含 `status`（`ok`、`error`、`refused`、`clarify`）、`sql`、`columns`、`rows`、`message`、`error_kind`、`refusal_source`。日期 MUST 序列化為 ISO 8601 字串，Decimal MUST 序列化為 JSON 數字。

#### Scenario: 成功
- **WHEN** 送出合法問題且流程成功
- **THEN** 回傳 HTTP 200、`status=ok`

#### Scenario: 不合法輸入
- **WHEN** 缺少 `question`、為空字串或超過 1000 字元
- **THEN** 回傳 HTTP 422

#### Scenario: SQL 被拒絕
- **WHEN** 模型產生的 SQL 未通過防護
- **THEN** 回傳 HTTP 200、`status=error` 與原因

#### Scenario: 拒答
- **WHEN** 輸入防護或模型拒答
- **THEN** 回傳 HTTP 200、`status=refused`、`sql=null`、空的 `columns`/`rows`、`message` 為原因、`refusal_source` 為 `input_guardrail` 或 `model`

#### Scenario: 反問
- **WHEN** 模型判斷問題缺少必要資訊
- **THEN** 回傳 HTTP 200、`status=clarify`、`sql=null`、空的 `columns`/`rows`、`message` 為反問、`refusal_source=null`

#### Scenario: 輸入檢查無法使用
- **WHEN** 已設定 Guardrail 但呼叫失敗
- **THEN** 回傳 HTTP 502 與「輸入檢查暫時無法使用，請稍後再試」，回應不含內部錯誤細節

#### Scenario: Bedrock 無法使用
- **WHEN** 呼叫 Bedrock 失敗
- **THEN** 回傳 HTTP 502，回應仍為完整合約（`status=error`、`sql=null`、空的 `columns`/`rows`、通用 `message`、`error_kind=null`、`refusal_source=null`），錯誤追蹤只記錄一次，回應不含內部錯誤細節

#### Scenario: 資料庫無法連線
- **WHEN** 連線池無法建立（資料庫未啟動、密碼錯誤）
- **THEN** 回傳 HTTP 503 與「資料庫暫時無法使用」，不誤報為模型錯誤；下一次提問會重新嘗試連線

#### Scenario: 服務關閉
- **WHEN** API 服務關閉
- **THEN** 關閉資料庫連線池
