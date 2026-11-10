## Why

企業導入 GenBI 時第一個會問的是「誰、什麼時候、問了什麼、執行了哪段 SQL」。目前每次提問只留下不含問題原文的應用程式 log 與指標（`observe-with-grafana`），無法回頭查某一題，也無法證明防護攔截（SQL 被拒、拒答）確實發生。加入稽核紀錄讓每次提問都可追溯，補上與企業版 GenBI 最大的落差之一；同一批資料也提供重複提問率與 token 數，作為之後評估 prompt caching 的依據。

## What Changes

- 新增稽核資料表 `ask_audit`：每次 `/api/ask` 一筆，記錄 request id、時間、訪客識別（IP 的 HMAC）、問題、最後一次的 SQL、先前失敗嘗試的 SQL 與原因、結果狀態、拒答來源、錯誤種類、攔截原因、模型 ID、token 數、Guardrail 文字單位、估算成本、耗時與回傳筆數
- 新增稽核角色 `genbi_audit_writer`：只能 INSERT 與 SELECT `ask_audit`，不能 UPDATE、DELETE，也讀不到任何業務資料表；`genbi_reader` 讀不到也改不了 `ask_audit`
- 每次提問同時輸出一行 `event=ask_audit` 的 JSON log（與 DB 紀錄同欄位），由 Alloy 送到 Grafana Cloud Loki，作為應用程式改不了的第二份紀錄；這是「log 不含問題原文」規則唯一的例外
- 管理者在 Grafana 的稽核 dashboard 查看紀錄；不新增 `/api/audit` 或前端紀錄頁，公開網址沒有任何讀取紀錄的入口
- 提問畫面註明「提問內容會被記錄以供稽核，請勿輸入個人資料」
- 稽核寫入失敗不影響回答使用者，但 MUST 記錄錯誤 log、計入指標並觸發告警

### Non-goals

- 使用者登入與身分（以 IP 的 HMAC 區分訪客；SSO 為後續工作）
- 依使用者身分限制資料（row-level security）
- 稽核紀錄的自動清除與保存期限（Demo 資料量小；Loki 依 Grafana Cloud 方案保存）
- 記錄被 nginx 限流或每日上限擋下的請求（沒有執行任何東西；已由 nginx access log 與指標記錄）

## Capabilities

### New Capabilities

- `audit-log`: 提問與 SQL 執行的稽核紀錄。

### Modified Capabilities

- `observability`: JSON log 不含問題原文的規則，新增 `event=ask_audit` 稽核 log 為唯一例外。

## Impact

- 新增：`db/init` 稽核資料表與角色、後端稽核寫入（`app/audit.py`）、稽核 dashboard、稽核寫入失敗的指標與告警
- 修改：`docker-compose.yml` 與 `.env.example`（`GENBI_AUDIT_WRITER_PASSWORD`、`AUDIT_IP_HMAC_KEY`）、nginx（轉發真實來源 IP）、`pipeline.AskResult`（保留先前失敗的嘗試）、提問畫面的提示文字
- 既有本機資料庫要 `docker compose down -v` 重建才會有稽核表與角色
- 依賴：`refuse-and-clarify`（拒答來源）、`self-correct-on-error`（重試）、`observe-with-grafana`（JSON log、Alloy、Loki）
