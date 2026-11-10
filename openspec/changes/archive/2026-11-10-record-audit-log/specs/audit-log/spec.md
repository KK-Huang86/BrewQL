## ADDED Requirements

### Requirement: 每次提問留下稽核紀錄
系統 SHALL 為每次進入 `/api/ask` handler 的提問寫入一筆稽核紀錄，包含 request id、時間、訪客識別、問題、最後一次嘗試的 SQL、先前失敗的嘗試（SQL、錯誤種類、原因）、結果狀態、拒答來源、錯誤種類、攔截原因、模型 ID、token 數、Guardrail 文字單位、估算成本、耗時與回傳筆數。被防護攔截、拒答、反問與服務無法使用（5xx）的提問 MUST 同樣被記錄。紀錄 MUST NOT 包含查詢結果資料。被每日上限擋下的請求不記錄。

#### Scenario: 成功的提問
- **WHEN** 使用者問「台北市有幾家咖啡店？」並成功取得結果
- **THEN** 稽核表新增一筆 `status=ok` 的紀錄，含實際執行的 SQL、筆數與 token 數

#### Scenario: 被 SQL 防護攔截後重試成功
- **WHEN** 第一次產生的 SQL 未通過防護，重試後成功
- **THEN** 紀錄的 `status=ok`，`failed_attempts` 有一筆 `error_kind=guardrail` 與被拒的 SQL

#### Scenario: 被輸入防護拒答
- **WHEN** 問題被 Guardrail 以 prompt attack 攔下
- **THEN** 紀錄的 `status=refused`、`refusal_source=input_guardrail`、`guardrail_reasons` 含 `prompt_attack`，`sql` 為空

#### Scenario: 服務無法使用
- **WHEN** Bedrock 無法連線，`/api/ask` 回 502
- **THEN** 紀錄的 `status=error`、`error_kind=unavailable_model`

#### Scenario: 每日上限
- **WHEN** 當天額度用完後又有一個問題
- **THEN** 回 429，稽核表沒有新增紀錄

#### Scenario: 同一筆重送
- **WHEN** 同一個 request id 的紀錄被寫入兩次
- **THEN** 稽核表只有一筆

### Requirement: 訪客識別不保存 IP
稽核紀錄 SHALL 以來源 IP 的 HMAC-SHA256（金鑰來自設定）識別訪客，MUST NOT 保存 IP 本身。來源 IP SHALL 取自 nginx 設定的 `X-Real-IP`，nginx MUST 以實際連線的來源 IP 覆寫該 header。

#### Scenario: 同一來源
- **WHEN** 同一個 IP 問了兩個問題
- **THEN** 兩筆紀錄的 `visitor` 相同，且都不含該 IP

#### Scenario: 偽造來源
- **WHEN** 使用者自己送出 `X-Real-IP: 1.2.3.4`
- **THEN** 紀錄的 `visitor` 是實際連線 IP 的 HMAC，不是 `1.2.3.4` 的

### Requirement: 結構化 JSON 稽核 log
每次寫入稽核紀錄前，系統 SHALL 輸出一行 `event` 為 `ask_audit` 的 JSON log，欄位與稽核紀錄相同。啟用可觀測性時，該 log SHALL 由 Alloy 送到 Grafana Cloud Loki，作為應用程式無法修改的第二份紀錄；Alloy 使用的 Grafana Cloud token MUST 只具寫入權限。

#### Scenario: 本機輸出
- **WHEN** 完成一次提問
- **THEN** 標準輸出有一行可被 JSON 解析、`event` 為 `ask_audit` 的 log，含問題、SQL 與狀態

#### Scenario: DB 稽核失敗
- **WHEN** DB 稽核寫入失敗
- **THEN** `ask_audit` log 仍然輸出

### Requirement: 紀錄只供管理者查看
公開網址 MUST NOT 提供任何讀取稽核紀錄的入口。管理者 SHALL 在 Grafana 的稽核 dashboard 查看紀錄，dashboard SHALL 以程式碼存在 `observability/dashboards/`。提問畫面 SHALL 註明提問內容會被記錄，請勿輸入個人資料。

#### Scenario: 訪客查詢紀錄
- **WHEN** 從公開網址請求 `/api/audit`
- **THEN** nginx 回 404，後端沒有收到請求

#### Scenario: 管理者查看
- **WHEN** 管理者在 Grafana 開啟稽核 dashboard
- **THEN** 看得到最近提問的時間、訪客識別、狀態、問題與 SQL

#### Scenario: 提問畫面提示
- **WHEN** 開啟提問畫面
- **THEN** 看得到「提問內容會被記錄以供稽核，請勿輸入個人資料」

### Requirement: 稽核寫入與查詢權限分離
稽核紀錄 MUST 由 `genbi_audit_writer` 寫入；該角色 SHALL 只具稽核表的 INSERT 與 SELECT 權限，MUST NOT 能修改或刪除稽核紀錄，MUST NOT 能讀取任何業務資料表。`genbi_reader` MUST NOT 能讀取或修改稽核表。

#### Scenario: 稽核角色讀取業務資料
- **WHEN** 以 `genbi_audit_writer` 執行 `SELECT * FROM cafes`
- **THEN** 資料庫拒絕

#### Scenario: 稽核角色竄改紀錄
- **WHEN** 以 `genbi_audit_writer` 更新或刪除稽核紀錄
- **THEN** 資料庫拒絕

#### Scenario: 查詢角色讀取紀錄
- **WHEN** 以 `genbi_reader` 讀取或刪除稽核紀錄
- **THEN** 資料庫拒絕

### Requirement: 稽核失敗不中斷回答
稽核寫入失敗或逾時（2 秒）時，系統 SHALL 照常回應使用者，MUST 記錄含 request id 的錯誤 log 並增加 `brewql_audit_write_failures_total`，MUST NOT 重試或靜默忽略。未設定稽核連線或 HMAC 金鑰時，backend MUST 拒絕啟動。

#### Scenario: 稽核資料庫無法連線
- **WHEN** 寫入稽核紀錄失敗
- **THEN** 使用者仍收到查詢結果，log 中有含 request id 的稽核失敗錯誤，`brewql_audit_write_failures_total` 加 1

#### Scenario: 稽核失敗告警
- **WHEN** 5 分鐘內稽核寫入失敗次數大於 0
- **THEN** 觸發稽核失敗的告警

#### Scenario: 缺少稽核設定
- **WHEN** 未設定 `AUDIT_DATABASE_URL` 或 `AUDIT_IP_HMAC_KEY` 就啟動 backend
- **THEN** backend 啟動失敗並說明缺少哪個設定
