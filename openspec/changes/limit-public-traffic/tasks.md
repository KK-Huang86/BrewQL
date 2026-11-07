## 1. nginx

- [ ] 1.1 `nginx.conf` 加入分級限流（`limit_req_zone`、`limit_conn_zone`）、429 JSON 回應與 `Retry-After`、請求大小與逾時；驗證：以 curl 迴圈實測 429、413，後端 log 沒有收到被擋的請求
- [ ] 1.2 nginx 改成白名單轉發（`location = /api/ask`，其餘 `/api/` 回 404），`/metrics`、`/health`、`/docs`、`/openapi.json` 明確回 404；驗證：經 nginx 逐一請求這些路徑與 `/api/audit` 都回 404 且後端 log 沒有收到，`/api/ask` 照常回應

## 2. 後端

- [ ] 2.1 測試 + 實作：全域每日提問上限（呼叫 Guardrail 前檢查、422 不計入、跨日重置、觸發時記錄 log），設定同步 `.env.example`；驗證：測試由紅轉綠

## 3. 前端

- [ ] 3.1 測試 + 實作：429 顯示 `message` 並恢復送出按鈕；驗證：測試由紅轉綠

## 4. 驗證

- [ ] 4.1 本機 compose 實測：連續提問觸發 429、等待後恢復、`DAILY_QUESTION_LIMIT=3` 時第 4 題回 429 且 log 沒有 Guardrail 呼叫；驗證：記錄結果
