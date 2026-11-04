## ADDED Requirements

### Requirement: 每次提問留下稽核紀錄
系統 SHALL 為每次 `/api/ask` 寫入一筆稽核紀錄，包含時間、問題、模型產生的 SQL、實際執行的 SQL、結果狀態、拒答或攔截來源、模型 ID、token 數、耗時與回傳筆數。被防護攔截或拒答的提問 MUST 同樣被記錄。

#### Scenario: 成功的提問
- **WHEN** 使用者問「台北市有幾家咖啡店？」並成功取得結果
- **THEN** 稽核表新增一筆 `status=ok` 的紀錄，含實際執行的 SQL 與筆數

#### Scenario: 被防護攔截
- **WHEN** 模型產生的 SQL 未通過防護
- **THEN** 稽核表新增一筆 `status=error` 的紀錄，含被拒的 SQL 與攔截原因

### Requirement: 結構化 JSON 稽核 log
每次 `/api/ask` 系統 SHALL 輸出一行 JSON 格式的稽核 log，欄位與 DB 稽核紀錄一致，並含 `event: "ask_audit"` 以便篩選。部署環境 SHALL 將該 log 送到 CloudWatch Logs，log group MUST 設定保存期限，應用程式使用的 IAM role MUST NOT 具有刪除 log 的權限。

#### Scenario: 本機輸出
- **WHEN** 完成一次提問
- **THEN** 標準輸出有一行可被 JSON 解析、`event` 為 `ask_audit` 的 log

#### Scenario: 上線後查詢
- **WHEN** 在 CloudWatch Logs Insights 以 `event = "ask_audit"` 篩選
- **THEN** 查得到每次提問的問題、SQL 與狀態

#### Scenario: DB 稽核失敗
- **WHEN** DB 稽核寫入失敗
- **THEN** JSON 稽核 log 仍然輸出

### Requirement: 稽核寫入與查詢權限分離
稽核紀錄 MUST 由只具 INSERT 權限的 `genbi_audit_writer` 寫入；該角色 MUST NOT 能讀取任何業務資料表，`genbi_reader` MUST NOT 能修改稽核表。

#### Scenario: 稽核角色讀取業務資料
- **WHEN** 以 `genbi_audit_writer` 執行 `SELECT * FROM cafes`
- **THEN** 資料庫拒絕

#### Scenario: 查詢角色竄改紀錄
- **WHEN** 以 `genbi_reader` 刪除稽核紀錄
- **THEN** 資料庫拒絕

### Requirement: 稽核失敗不中斷回答
稽核寫入失敗時，系統 SHALL 照常回應使用者，並 MUST 記錄錯誤 log，MUST NOT 靜默忽略。

#### Scenario: 稽核資料庫無法連線
- **WHEN** 寫入稽核紀錄失敗
- **THEN** 使用者仍收到查詢結果，log 中有稽核失敗的錯誤
