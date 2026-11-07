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
每次 `/api/ask` 系統 SHALL 輸出一行 JSON 格式的稽核 log，欄位與 DB 稽核紀錄一致，並含 `event: "ask_audit"` 以便篩選。啟用可觀測性時，該 log SHALL 由 Alloy 送到 Grafana Cloud Loki，作為應用程式無法修改的第二份紀錄；Grafana Cloud 的 token MUST 只具寫入權限。

#### Scenario: 本機輸出
- **WHEN** 完成一次提問
- **THEN** 標準輸出有一行可被 JSON 解析、`event` 為 `ask_audit` 的 log

#### Scenario: 上線後查詢
- **WHEN** 在 Grafana 以 `event="ask_audit"` 篩選 Loki 的 log
- **THEN** 查得到每次提問的問題、SQL 與狀態

#### Scenario: DB 稽核失敗
- **WHEN** DB 稽核寫入失敗
- **THEN** JSON 稽核 log 仍然輸出

### Requirement: 紀錄只供管理者查看
提問紀錄包含其他訪客輸入的文字，公開網址 MUST NOT 能存取紀錄查詢（`GET /api/audit` 與紀錄頁）；管理者 SHALL 透過 SSH tunnel 直接連 backend 查看。提問畫面 SHALL 註明提問內容會被記錄，請勿輸入個人資料。

#### Scenario: 訪客查詢紀錄
- **WHEN** 從公開網址請求 `/api/audit`
- **THEN** nginx 回 403 或 404，後端沒有收到請求

#### Scenario: 提問畫面提示
- **WHEN** 開啟提問畫面
- **THEN** 看得到「提問內容會被記錄以供稽核，請勿輸入個人資料」

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
