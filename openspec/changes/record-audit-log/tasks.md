## 1. 資料庫

- [x] 1.1 `db/init/04_audit.sh`：`ask_audit` 資料表與 `genbi_audit_writer` 角色；compose 與 `db/test-db.sh` 傳入 `GENBI_AUDIT_WRITER_PASSWORD`，`.env.example` 同步；驗證：整合測試確認寫入角色讀不到 `cafes`、改不了也刪不了稽核紀錄，`genbi_reader` 讀不到稽核表
  - 結果：`tests/integration/test_audit_roles.py` 7 個案例（寫入角色可新增並讀回、讀不到 `cafes`、UPDATE／DELETE／TRUNCATE 被拒；`genbi_reader` 在解除唯讀預設後 SELECT／DELETE 仍被拒，證明擋下的是權限而不是唯讀模式）。紅燈原因為角色不存在；整合測試共 37 個通過，模擬資料檢查全部通過。CI 與 `db/test-db.sh` 同步執行 `04_audit.sh`。

## 2. 後端

- [x] 2.1 測試 + 實作：`AskResult.failed_attempts` 保留重試前失敗的嘗試；驗證：測試由紅轉綠
  - 結果：`test_pipeline_retry.py` 新增 3 個案例（重試成功後保留被拒的 SQL、用完重試時最後一次是結果本身不重複記錄、第一次就成功時為空）。紅燈原因為沒有該欄位；欄位 `compare=False`，`AskResponse` 忽略多餘欄位，API 回應不變。後端 438 個測試通過。
- [x] 2.2 測試 + 實作：`app/audit.py` 把一次提問轉成稽核紀錄（各種結果、5xx、HMAC visitor、不含結果資料）；驗證：測試由紅轉綠
  - 結果：`tests/test_audit.py` 9 個案例（成功含 SQL、筆數、token、成本；失敗嘗試轉成純資料；不含結果資料；輸入防護攔截含原因、無 SQL；單價未知記為 NULL；5xx 只記種類與耗時、成本未知；visitor 與 openssl 算出的 HMAC 相同、不含 IP、隨金鑰改變；沒有 IP 時為 NULL）。紅燈原因為模組不存在；後端 447 個測試通過。
- [ ] 2.3 測試 + 實作：handler 在回應前先輸出 `ask_audit` JSON log、再寫入稽核；每日上限的 429 不記錄；其他 log 不含問題原文；驗證：測試由紅轉綠
- [ ] 2.4 測試 + 實作：稽核寫入失敗或逾時仍回應使用者，記錄含 request id 的錯誤 log、`brewql_audit_write_failures_total` 加 1（從 0 開始）；驗證：測試由紅轉綠
- [ ] 2.5 測試 + 實作：Postgres 稽核寫入（`ON CONFLICT DO NOTHING`、2 秒逾時）；驗證：整合測試寫入兩次同一 request id 只有一筆
- [ ] 2.6 測試 + 實作：缺少 `AUDIT_DATABASE_URL` 或 `AUDIT_IP_HMAC_KEY`（少於 32 字元）時啟動失敗；compose 與 `.env.example` 同步；驗證：測試由紅轉綠

## 3. 來源 IP 與畫面

- [ ] 3.1 測試 + 實作：nginx 以 `X-Real-IP $remote_addr` 覆寫來源 IP；驗證：nginx 容器測試中使用者送的 `X-Real-IP` 被蓋掉
- [ ] 3.2 測試 + 實作：提問畫面顯示稽核提示；驗證：前端測試由紅轉綠

## 4. Grafana

- [ ] 4.1 稽核 dashboard（`observability/dashboards/brewql-audit.json`）與稽核失敗告警；驗證：本機提問後在 Grafana 看到紀錄，停掉稽核資料庫連線後告警觸發
- [ ] 4.2 查證 Grafana Cloud Loki 的保存期限與 token 權限，記入 `observability/README.md`；驗證：README 記錄查證結果與來源

## 5. 驗證

- [ ] 5.1 `docker compose down -v` 重建後實際提問各種類型，比對 DB 與 Loki 的紀錄一致；README 補上稽核說明與管理者用 psql 查詢的方式；驗證：每種結果都有一筆且兩份紀錄欄位相同
