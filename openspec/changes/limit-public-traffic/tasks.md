## 1. nginx

- [x] 1.1 nginx 設定改為模板 `frontend/nginx/default.conf.template`（D8），容器測試骨架 + 白名單轉發（D6、D7）：`/api/ask` 轉發、前端頁面照常，`/metrics`、`/health`、`/docs`、`/openapi.json`、`/api/audit`、`/api/anything-new` 回 404 且假 backend 沒收到；驗證：測試紅燈（目前整個 `/api/` 都轉發、其他路徑落到 SPA），改設定後綠燈
- [x] 1.2 `/api/ask` 限流與 429 合約（D1、D2、D8）：20 次連續提問 6 通過 14 被擋、429 JSON body 與 `Retry-After`、第二個來源 IP 不受影響、`ASK_RATE_BURST=2` 時只放行 3 次、不合法的值讓 nginx 啟動失敗；同時連線上限寫進設定；Dockerfile 預設值、compose 與 `.env.example`；驗證：紅燈再綠燈
- [x] 1.3 請求大小與逾時（D5）：1 MB body 回 413 且假 backend 沒收到；驗證：紅燈再綠燈
- [x] 1.4 CI frontend job 執行 nginx 容器測試；驗證：PR 上的 frontend check 跑過這些測試

## 2. 後端

- [x] 2.1 每日計數器（D3）：未滿放行並計數、達上限拒絕、台北午夜重置、`Retry-After` 秒數；驗證：紅燈再綠燈（注入時間，不等真的跨日）
- [x] 2.2 `/api/ask` 接上計數器：達上限回 429 合約且 Guardrail 與模型沒被呼叫、422 不計入、拒答與錯誤計入、WARNING log；`DAILY_QUESTION_LIMIT` 設定與驗證，同步 `.env.example` 與 compose；驗證：紅燈再綠燈

## 3. 前端

- [ ] 3.1 429 顯示 `message` 並恢復送出按鈕；驗證：既有錯誤路徑若已支援，以 `test:` 單獨 commit 並附突變驗證，否則紅燈再綠燈

## 4. 驗證

- [ ] 4.1 本機 compose 實測：瀏覽器連續提問看到「請求太頻繁」、等待後恢復；`DAILY_QUESTION_LIMIT=3` 時第 4 題回「今日提問次數已達上限」且 backend log 沒有 Guardrail 呼叫；驗證：記錄結果
