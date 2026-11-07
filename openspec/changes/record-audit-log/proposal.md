## Why

企業導入 GenBI 時第一個會問的是「誰、什麼時候、問了什麼、執行了哪段 SQL」。目前每次提問只留在應用程式 log，無法查詢、也不保證保存。加入稽核紀錄讓每次提問都可追溯，也讓防護攔截（SQL 被拒、拒答）有據可查，補上與企業版 GenBI 最大的落差之一。

## What Changes

- 新增稽核資料表：每次 `/api/ask` 記錄時間、問題、產生與實際執行的 SQL、結果狀態、拒答／攔截來源、模型 ID、token 數、耗時、筆數
- 新增只能寫入稽核表的資料庫角色 `genbi_audit_writer`（INSERT only，不能讀任何業務資料表）；API 查詢仍只用 `genbi_reader`
- 每次提問同時輸出一行結構化 JSON log（與 DB 紀錄同欄位）；由 `observe-with-grafana` 的 Alloy 送到 Grafana Cloud Loki，作為應用程式無法修改的第二份紀錄（取代原本規劃的 CloudWatch，只保留一條 log 管線）
- 提問畫面註明「提問內容會被記錄以供稽核，請勿輸入個人資料」
- 紀錄查詢（`GET /api/audit` 與紀錄頁）只供管理者：公開網址的 nginx 擋下，管理者透過 SSH tunnel 存取
- 稽核寫入失敗不影響回答使用者，但 MUST 記錄錯誤 log
- 營運人員可在介面查看最近的提問紀錄（唯讀）

### Non-goals

- 使用者登入與身分（目前以匿名 session 識別；SSO 為後續工作）
- 依使用者身分限制資料（row-level security）

## Capabilities

### New Capabilities

- `audit-log`: 提問與 SQL 執行的稽核紀錄。

### Modified Capabilities

（無）

## Impact

- 新增：稽核資料表與角色（db/init）、後端稽核寫入與 JSON log、介面紀錄頁
- 修改：nginx（公開網址擋下紀錄查詢）
- 依賴 ticket：`refuse-and-clarify`（記錄拒答來源）、`self-correct-on-error`（記錄重試次數）；第二份紀錄依賴 `observe-with-grafana`
