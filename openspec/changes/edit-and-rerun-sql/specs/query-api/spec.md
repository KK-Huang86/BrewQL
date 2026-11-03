## ADDED Requirements

### Requirement: 執行 SQL 端點
系統 SHALL 提供 `POST /api/sql`，請求為 `{"sql": string}`（1~10000 字元），套用與提問相同的 `sql-guardrails` 後執行，MUST NOT 呼叫模型。回應格式 SHALL 與提問端點相同（含 `chart`）。防護拒絕或執行失敗 SHALL 回傳 HTTP 200 與 `status=error`。

#### Scenario: 合法 SQL
- **WHEN** 送出 `SELECT district, COUNT(*) FROM cafes GROUP BY district`
- **THEN** 回傳 `status=ok`、結果與 `chart`

#### Scenario: 不安全 SQL
- **WHEN** 送出 `DROP TABLE cafes`
- **THEN** 回傳 `status=error`、`error_kind=guardrail`，資料庫未收到查詢

#### Scenario: 空 SQL
- **WHEN** 送出 `{"sql": ""}`
- **THEN** 回傳 HTTP 422

#### Scenario: 不呼叫模型
- **WHEN** 呼叫 `/api/sql`
- **THEN** Bedrock 沒有被呼叫
