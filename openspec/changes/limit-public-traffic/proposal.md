## Why

公開網址上線後，任何人都能提問，而每個問題都會花錢（Guardrail + Bedrock 模型）並佔用資料庫。沒有限制的話，一支簡單的迴圈腳本就能讓帳單暴增或讓服務變慢（cost DoS）。AWS Budgets 只會在事後通知，擋不住正在發生的濫用。需要在請求進入後端前就限制頻率，並在應用程式層設一個全域的每日上限，作為最後一道成本防線。

## What Changes

- nginx 依來源 IP 限流，依端點成本分級：
  - `/api/ask`（與之後的串流端點）：最嚴格，會呼叫 Guardrail 與模型
  - `/api/sql`（`edit-and-rerun-sql`）：中等，只用到資料庫
  - 其他 `/api/`：寬鬆
  - 每個 IP 的同時連線數上限；串流端點另設更低的同時連線上限
- 超過限制回 HTTP 429，body 與既有回應合約同形（`message`：「請求太頻繁，請稍後再試」），附 `Retry-After`
- 請求大小上限與 client 逾時，避免超大或極慢的請求佔住連線
- 應用程式層的**全域每日提問上限**（可設定）：達到後回 429「今日提問次數已達上限」，不呼叫 Guardrail 與模型
- 內部端點不經 nginx 對外：`/metrics`、`/health` 以外的管理用途端點（例如之後的稽核查詢）

### Non-goals

- WAF、CAPTCHA、登入：Demo 規模不需要
- 分散式限流（Redis）：單一主機，nginx 記憶體內計數即可

## Capabilities

### New Capabilities

- `public-access-limits`: 公開端點的限流、請求大小限制、全域每日上限，以及 HTTP 429 的回應合約。

### Modified Capabilities

- `query-web-ui`: 收到 429 時顯示原因。

## Impact

- 修改：`frontend/nginx.conf`、`backend/app/main.py`（每日上限）、前端錯誤顯示
- 新設定：`DAILY_QUESTION_LIMIT`（同步 `.env.example`）
- 本機開發也套用相同的 nginx 設定；評估腳本（`eval-golden-set`）直接呼叫流程或 backend，不經 nginx，不受限流影響
- 依賴 ticket：`refuse-and-clarify`；`deploy-public-demo` 依賴本 ticket
