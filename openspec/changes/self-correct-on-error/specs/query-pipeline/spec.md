## ADDED Requirements

### Requirement: 有上限的自動修正
當 SQL 被防護拒絕、資料庫執行失敗或模型回覆不合格式時，系統 SHALL 把先前的回覆與錯誤原因連同原問題回饋給模型重新產生，最多重試 `MAX_SQL_RETRIES` 次（預設 2，即最多 3 次嘗試）。每次產生的 SQL MUST 重新經過 SQL 防護；被防護拒絕的 SQL MUST NOT 被執行。用盡後 MUST 回傳 `status=error`、最後一次的 SQL、`error_kind` 與錯誤訊息。執行逾時、Bedrock 服務錯誤與輸入 Guardrail 無法使用 MUST NOT 觸發重試。結果 SHALL 包含 `attempts`（模型被呼叫的次數）。

#### Scenario: 防護拒絕後修正成功
- **WHEN** 第一次產生 `DELETE FROM cafes`，第二次產生合法 SQL
- **THEN** 回傳 `status=ok`、`attempts=2`；第二次產生時收到第一次的 SQL 與防護訊息；資料庫只執行一次

#### Scenario: 執行錯誤後修正成功
- **WHEN** 第一次執行回報欄位不存在，第二次成功
- **THEN** 回傳 `status=ok`、`attempts=2`，第二次產生時收到資料庫錯誤訊息

#### Scenario: 格式錯誤後修正成功
- **WHEN** 第一次回覆不合格式，第二次產生合法 SQL
- **THEN** 回傳 `status=ok`、`attempts=2`

#### Scenario: 重試用盡
- **WHEN** 每次都產生被拒絕的 SQL，上限為 2
- **THEN** 3 次嘗試後回傳 `status=error`、`attempts=3`、`error_kind=guardrail`、最後一次的 SQL，資料庫未執行任何查詢

#### Scenario: 不重試
- **WHEN** 上限為 0 且第一次失敗
- **THEN** 回傳 `status=error`、`attempts=1`

#### Scenario: 逾時不重試
- **WHEN** 第一次執行超過 statement_timeout
- **THEN** 回傳 `status=error`、`error_kind=query`、`attempts=1`，模型只被呼叫一次

#### Scenario: 服務錯誤不重試
- **WHEN** 第一次呼叫 Bedrock 就發生服務錯誤
- **THEN** 錯誤往外拋出，模型只被呼叫一次

#### Scenario: 拒答不重試
- **WHEN** 第一次回覆為拒答
- **THEN** 回傳 `status=refused`、`attempts=1`

#### Scenario: 重試中改為拒答
- **WHEN** 第一次 SQL 被防護拒絕，第二次回覆為拒答
- **THEN** 回傳 `status=refused`、`refusal_source=model`、`attempts=2`

#### Scenario: 輸入 Guardrail 攔下
- **WHEN** 問題被輸入 Guardrail 擋下
- **THEN** 回傳 `status=refused`、`attempts=0`，模型沒有被呼叫

### Requirement: 重試上限設定
`MAX_SQL_RETRIES` SHALL 為 0～5 的整數，預設 2；超出範圍 MUST 在啟動時視為設定錯誤。

#### Scenario: 負數
- **WHEN** `MAX_SQL_RETRIES=-1`
- **THEN** 載入設定失敗

#### Scenario: 超過上限
- **WHEN** `MAX_SQL_RETRIES=6`
- **THEN** 載入設定失敗

### Requirement: 重試紀錄
每次失敗的嘗試 SHALL 以 warning 記錄嘗試編號、錯誤類型、錯誤原因與當次 SQL，MUST NOT 記錄使用者問題。

#### Scenario: 留下紀錄
- **WHEN** 某次嘗試被防護拒絕
- **THEN** log 中有嘗試編號、`guardrail`、原因與 SQL，且沒有問題原文
