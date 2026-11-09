## Why

公開網址上線後，任何人都能提問，而每個問題都會花錢（Guardrail + Bedrock 模型）並佔用資料庫。沒有限制的話，一支簡單的迴圈腳本就能讓帳單暴增或讓服務變慢（cost DoS）。AWS Budgets 只會在事後通知，擋不住正在發生的濫用。需要在請求進入後端前就限制頻率，並在應用程式層設一個全域的每日上限，作為最後一道成本防線。

## What Changes

- nginx 依來源 IP 限流：`/api/ask` 預設每分鐘 10 次（burst 5、`nodelay`）；每個 IP 同時連線預設最多 20。數值由環境變數 `ASK_RATE_PER_MINUTE`、`ASK_RATE_BURST`、`MAX_CONNECTIONS_PER_IP` 設定（nginx 設定檔改為模板）。之後的 `/api/sql`、串流端點依同一張分級表在各自的 ticket 加上
- 超過限制回 HTTP 429，body 與既有回應合約同形（`message`：「請求太頻繁，請稍後再試」），附 `Retry-After`
- 請求大小上限與 client 逾時，避免超大或極慢的請求佔住連線
- 應用程式層的**全域每日提問上限**（`DAILY_QUESTION_LIMIT`，台北時間每日重置）：達到後回 429「今日提問次數已達上限，請明天再試」，不呼叫 Guardrail 與模型
- nginx 以白名單轉發：只有 `/api/ask` 會轉給 backend；`/metrics`、`/health`、`/docs`、`/openapi.json` 與其他 `/api/` 路徑一律回 404
- nginx 行為的容器測試，在 CI 執行

### Non-goals

- WAF、CAPTCHA、登入：Demo 規模不需要
- 分散式限流（Redis）：單一主機，nginx 記憶體內計數即可
- 還不存在的端點的限流設定、Prometheus 指標（由後續 ticket 加上）

## Capabilities

### New Capabilities

- `public-access-limits`: 公開端點的限流、請求大小限制、全域每日上限、白名單轉發，以及 HTTP 429 的回應合約。

### Modified Capabilities

- `query-web-ui`: 收到 429 時顯示原因。

## Impact

- 修改：`frontend/Dockerfile`、`backend/app/main.py`、`backend/app/config.py`、`docker-compose.yml`、`.github/workflows/frontend.yml`
- 搬移：`frontend/nginx.conf` → `frontend/nginx/default.conf.template`
- 新增：`backend/app/daily_limit.py`、`frontend/nginx-tests/`
- 新設定：`ASK_RATE_PER_MINUTE`、`ASK_RATE_BURST`、`MAX_CONNECTIONS_PER_IP`、`DAILY_QUESTION_LIMIT`（同步 `.env.example` 與 compose）
- 本機開發也套用相同的 nginx 設定；評估腳本直接呼叫 pipeline，不受限流與每日上限影響
- 依賴 ticket：`refuse-and-clarify`；`deploy-public-demo` 依賴本 ticket
