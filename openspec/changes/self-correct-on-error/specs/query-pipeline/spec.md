## ADDED Requirements

### Requirement: 有上限的自動修正
當 SQL 被防護拒絕、資料庫執行失敗或模型沒產生 SQL 時，系統 SHALL 把錯誤訊息連同原問題回饋給模型重新產生，最多重試設定次數（預設 2，即最多 3 次嘗試）。用盡後 MUST 回傳 `status=error`、最後一次 SQL 與錯誤訊息。被防護拒絕的 SQL MUST NOT 被執行。重試次數為負數 MUST 視為設定錯誤。Bedrock 服務錯誤 MUST NOT 觸發重試。回應 SHALL 包含 `attempts`。

#### Scenario: 防護拒絕後修正成功
- **WHEN** 第一次產生 `DELETE FROM cafes`，第二次產生合法 SQL
- **THEN** 回傳 `status=ok`、`attempts=2`；第二次產生時收到第一次的錯誤原因；資料庫只執行一次

#### Scenario: 執行錯誤後修正成功
- **WHEN** 第一次執行回報欄位不存在，第二次成功
- **THEN** 回傳 `status=ok`，第二次產生時收到資料庫錯誤訊息

#### Scenario: 重試用盡
- **WHEN** 每次都產生被拒絕的 SQL，上限為 2
- **THEN** 3 次嘗試後回傳 `status=error`，資料庫未執行任何查詢

#### Scenario: 不重試
- **WHEN** 上限為 0 且第一次失敗
- **THEN** 回傳 `status=error`、`attempts=1`

#### Scenario: 服務錯誤不重試
- **WHEN** 第一次呼叫 Bedrock 就發生服務錯誤
- **THEN** 錯誤往外拋出，模型只被呼叫一次

#### Scenario: 拒答不重試
- **WHEN** 第一次回覆為拒答
- **THEN** 回傳 `status=refused`、`attempts=1`

### Requirement: 重試紀錄
每次失敗的嘗試 SHALL 記錄嘗試編號、錯誤類型、錯誤原因與當次 SQL。

#### Scenario: 留下紀錄
- **WHEN** 某次嘗試被防護拒絕
- **THEN** log 中有嘗試編號、`guardrail`、原因與 SQL
