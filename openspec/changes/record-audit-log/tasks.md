## 1. 資料庫

- [x] 1.1 `db/init/04_audit.sh`：`ask_audit` 資料表與 `genbi_audit_writer` 角色；compose 與 `db/test-db.sh` 傳入 `GENBI_AUDIT_WRITER_PASSWORD`，`.env.example` 同步；驗證：整合測試確認寫入角色讀不到 `cafes`、改不了也刪不了稽核紀錄，`genbi_reader` 讀不到稽核表
  - 結果：`tests/integration/test_audit_roles.py` 7 個案例（寫入角色可新增並讀回、讀不到 `cafes`、UPDATE／DELETE／TRUNCATE 被拒；`genbi_reader` 在解除唯讀預設後 SELECT／DELETE 仍被拒，證明擋下的是權限而不是唯讀模式）。紅燈原因為角色不存在；整合測試共 37 個通過，模擬資料檢查全部通過。CI 與 `db/test-db.sh` 同步執行 `04_audit.sh`。

## 2. 後端

- [x] 2.1 測試 + 實作：`AskResult.failed_attempts` 保留重試前失敗的嘗試；驗證：測試由紅轉綠
  - 結果：`test_pipeline_retry.py` 新增 3 個案例（重試成功後保留被拒的 SQL、用完重試時最後一次是結果本身不重複記錄、第一次就成功時為空）。紅燈原因為沒有該欄位；欄位 `compare=False`，`AskResponse` 忽略多餘欄位，API 回應不變。後端 438 個測試通過。
- [x] 2.2 測試 + 實作：`app/audit.py` 把一次提問轉成稽核紀錄（各種結果、5xx、HMAC visitor、不含結果資料）；驗證：測試由紅轉綠
  - 結果：`tests/test_audit.py` 9 個案例（成功含 SQL、筆數、token、成本；失敗嘗試轉成純資料；不含結果資料；輸入防護攔截含原因、無 SQL；單價未知記為 NULL；5xx 只記種類與耗時、成本未知；visitor 與 openssl 算出的 HMAC 相同、不含 IP、隨金鑰改變；沒有 IP 時為 NULL）。紅燈原因為模組不存在；後端 447 個測試通過。
- [x] 2.3 測試 + 實作：handler 在回應前先輸出 `ask_audit` JSON log、再寫入稽核；每日上限的 429 不記錄；其他 log 不含問題原文；驗證：測試由紅轉綠
  - 結果：`tests/test_api_audit.py` 8 個案例（先 log 後寫入、log 欄位與紀錄一致、每題不同 request id、5xx 記為 outage、每日上限 429 不記錄、visitor 取自 `X-Real-IP` 或連線位址、重試流程中只有 `ask_audit` 那一行含問題原文）。紅燈原因為 `create_app` 沒有稽核參數；綠燈前修正兩個測試本身的錯誤期望（另外 commit）。問題外洩測試做過 mutation：在 handler 多 log 一次問題即失敗。後端 455 個測試通過。
- [x] 2.4 測試 + 實作：稽核寫入失敗或逾時仍回應使用者，記錄含 request id 的錯誤 log、`brewql_audit_write_failures_total` 加 1（從 0 開始）；驗證：測試由紅轉綠
  - 結果：`tests/test_api_audit.py` 新增 4 個案例（指標從 0 開始；寫入失敗仍回 200、只呼叫一次、指標加 1、錯誤 log 的 request id 對得上 `ask_audit` 那行且不含問題；寫入卡住時逾時、仍回 200；5xx 的回應不受稽核失敗影響）。紅燈原因為寫入失敗變成 500、指標不存在；綠燈前修正測試擷取 log 的等級（另外 commit）。錯誤 log 只記例外類型：資料庫錯誤訊息可能引用整筆資料而含問題。後端 459 個測試通過。
- [x] 2.5 測試 + 實作：Postgres 稽核寫入（`ON CONFLICT DO NOTHING`、2 秒逾時）；驗證：整合測試寫入兩次同一 request id 只有一筆
  - 結果：`PgAuditWriter`（asyncpg pool `max_size=2`、第一次寫入才連線）；`tests/integration/test_audit_writer.py` 4 個案例（每個欄位寫入正確、未知值保持 NULL、同一 request id 寫兩次只有一筆、連不上時丟出例外交給 handler 回報）。2 秒上限由 handler 的 `wait_for` 與角色的 `statement_timeout` 共同負責。mutation：拿掉 `ON CONFLICT DO NOTHING` 重複寫入測試即失敗。整合測試 41 個、單元測試 460 個通過。
- [x] 2.6 測試 + 實作：缺少 `AUDIT_DATABASE_URL` 或 `AUDIT_IP_HMAC_KEY`（少於 32 字元）時啟動失敗；compose 與 `.env.example` 同步；驗證：測試由紅轉綠
  - 結果：`build_app` 檢查兩個設定後才建 `PgAuditWriter`（Settings 欄位可留空，因 eval／smoke 共用）；關閉時 lifespan 一併關 audit pool；compose 對 `AUDIT_IP_HMAC_KEY` 用 `:?` 擋空值；`tests/test_build_app_audit.py` 5 個測試紅轉綠，全套 465 passed

## 3. 來源 IP 與畫面

- [x] 3.1 測試 + 實作：nginx 以 `X-Real-IP $remote_addr` 覆寫來源 IP；驗證：nginx 容器測試中使用者送的 `X-Real-IP` 被蓋掉
  - 結果：`/api/ask` 加 `proxy_set_header X-Real-IP $remote_addr`；fake backend 回傳收到的 `X-Real-IP`，`SourceIpTest` 2 個測試紅轉綠（使用者送 `203.0.113.66` 被換成 nginx 看到的位址）；nginx 測試 18 個全過
- [x] 3.2 測試 + 實作：提問畫面顯示稽核提示；驗證：前端測試由紅轉綠
  - 結果：提問框下方固定顯示「提問內容會被記錄以供稽核，請勿輸入個人資料」（`.audit-notice`，與修正次數同樣的淡色小字）；`AskPage.test.tsx` 新增 1 個案例紅轉綠（紅燈原因為找不到文字）；前端 62 個測試、lint、build 通過

## 4. Grafana

- [ ] 4.1 稽核 dashboard（`observability/dashboards/brewql-audit.json`）與稽核失敗告警；驗證：本機提問後在 Grafana 看到紀錄，停掉稽核資料庫連線後告警觸發
- [ ] 4.2 查證 Grafana Cloud Loki 的保存期限與 token 權限，記入 `observability/README.md`；驗證：README 記錄查證結果與來源

## 5. 驗證

- [ ] 5.1 `docker compose down -v` 重建後實際提問各種類型，比對 DB 與 Loki 的紀錄一致；README 補上稽核說明與管理者用 psql 查詢的方式；驗證：每種結果都有一筆且兩份紀錄欄位相同
