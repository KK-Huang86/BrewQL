## Context

nginx 在前端容器內，同時提供靜態檔與轉發 `/api/`（目前轉發整個 `/api/`，沒有任何限制）；部署時 EC2 直接對外，前面沒有 CloudFront 或 ALB。後端是單一 uvicorn process，目前只有 `GET /health` 與 `POST /api/ask` 兩個端點，FastAPI 預設還有 `/docs`、`/openapi.json`。compose 把 backend 的 8000 發布在 `127.0.0.1`，本機開發與評估直接打 backend，不經過 nginx。

評估（`python -m evaluation`）直接呼叫 pipeline，不經過 HTTP，不受限流與每日上限影響。

## Goals / Non-Goals

**Goals:** 單一來源無法把費用或服務打爆；分散來源的濫用也有每日成本上限；被限流的使用者看得懂原因；nginx 的行為有自動測試，不只靠手動 curl。

**Non-Goals:**
- 防禦大規模 DDoS（交給 AWS Shield Standard 的預設保護與關機）。
- 還不存在的端點（`/api/sql`、串流）的限流：由 `edit-and-rerun-sql`、`show-definitions-and-steps` 依 D1 的表加上自己的 `location`。
- 指標：每日上限觸發只記 log，Prometheus 指標由 `observe-with-grafana` 加上。

## Decisions

### D1. 依端點成本分級限流
| 端點 | 每 IP 速率 | burst | 狀態 |
|---|---|---|---|
| `/api/ask` | 10 次／分鐘 | 5（`nodelay`） | 本 ticket 實作 |
| `/api/sql` | 30 次／分鐘 | 10（`nodelay`） | `edit-and-rerun-sql` 實作 |
| 串流端點 | 10 次／分鐘，同時最多 2 條 | 5（`nodelay`） | `show-definitions-and-steps` 實作 |
| 靜態檔 | 不限速率 | — | 由同時連線數限制 |

- 每個 IP 同時連線最多 20（`limit_conn`），套用在整個 server。
- `nodelay`：額度內的 burst 立即轉發，超過的直接 429。不加 `nodelay` 時超出的請求會排隊，10 次／分鐘代表每 6 秒放行一個，使用者會看到請求卡住。
- 實際效果：同一 IP 連續送出 20 次 `/api/ask`，前 6 次（1 + burst 5）轉發，其餘 14 次 429。
- 限流數值由環境變數設定（D8），預設值即上表。

### D2. 429 回應與合約同形
`limit_req_status 429`、`limit_conn_status 429`，`error_page 429` 導到一個內部 location，回傳 `application/json`：`{"status":"error","sql":null,"columns":[],"rows":[],"message":"請求太頻繁，請稍後再試","error_kind":null,"refusal_source":null}`，並以 `add_header ... always` 附 `Retry-After: 60`（nginx 限流本身不會加這個 header）。前端既有錯誤路徑會顯示 `message`。

### D3. 全域每日上限放在應用程式
nginx 只能依 IP 計數，擋不住多個 IP 分散提問。後端在呼叫 Guardrail 之前檢查當日已處理的提問數：
- 日期以**台北時間**計算，與 system prompt 的「今天」一致，管理者看到的「今天」也一樣。
- 未滿上限：計數 +1 後照常處理；Guardrail 拒答、模型拒答、反問、錯誤都算一次（都已經花錢或佔資源）。
- 已達上限：回 HTTP 429、`message`「今日提問次數已達上限，請明天再試」、`Retry-After` 為距離台北午夜的秒數，不呼叫 Guardrail 或模型；記錄 WARNING log（含當日計數與上限）。
- 422（不合法的問題）在進入 handler 前就被 FastAPI 擋下，不計入。
- `DAILY_QUESTION_LIMIT` 預設 500，必須是正整數，否則啟動失敗（設定錯誤不能變成「沒有上限」）。以 ticket 8 的實測每題約 US$0.004，上限約等於每天 US$2。
- 計數放在記憶體：單一 process、單一 event loop，「檢查 + 計數」之間沒有 `await`，不會有併發競爭。重啟會歸零，但重啟需要管理者操作，可接受。
- 替代方案：存在資料庫 → 需要可寫入的角色，違反 API 只用 `genbi_reader` 的原則。
- 計數器是獨立的小類別（注入目前時間），單元測試不需要等到真的跨日。

### D4. 用 `$binary_remote_addr` 識別來源
EC2 直接對外，連線來源就是真實 IP。若之後前面加上 CloudFront 或 ALB，MUST 改用 `real_ip` 模組並只信任該 proxy 的位址，否則所有人會共用同一個限流額度，或者可以偽造 `X-Forwarded-For` 繞過限流。

### D5. 請求大小與逾時
`client_max_body_size 16k`（問題最多 1000 字，JSON 不會超過）；`client_body_timeout`、`client_header_timeout` 10 秒，降低慢速連線佔住 worker 的風險。

### D6. 白名單轉發，內部端點不對外
nginx 只把明確列出的公開 API 轉給 backend（`location = /api/ask`），其餘 `/api/` 一律回 404。前端靜態檔由 nginx 自己提供；`/metrics`、`/health`、`/docs`、`/openapi.json` MUST 明確回 404，不能落到前端 SPA 的 fallback（否則會回 200 的 `index.html`）。管理用途端點（例如稽核查詢）不加進白名單，管理者透過 SSH tunnel 直接連 backend。
- 為什麼不用黑名單（轉發整個 `/api/` 再 `deny` 特定路徑）：新增端點時忘了 `deny` 就會直接公開。白名單讓新端點預設不公開，要主動加入才會開放。
- repo 是公開的，路徑名稱無法保密，所以不能靠路徑難猜來保護。
- nginx 只擋得住經過 nginx 的流量：backend 的 8000 只能綁在 `127.0.0.1`（compose 已是如此），`deploy-public-demo` 的 security group 也不可開放 8000。

### D8. 限流數值用環境變數
`ASK_RATE_PER_MINUTE`（預設 10）、`ASK_RATE_BURST`（預設 5）、`MAX_CONNECTIONS_PER_IP`（預設 20）。部署後調整只改 `.env` 再重啟，不需要重新 build image。
- nginx 官方 image 啟動時會把 `/etc/nginx/templates/*.template` 以 `envsubst` 產生到 `conf.d/`，只替換有定義的環境變數，nginx 自己的 `$binary_remote_addr` 等不受影響。設定檔從 `frontend/nginx.conf` 改為 `frontend/nginx/default.conf.template`。
- 預設值寫在 Dockerfile 的 `ENV`，compose 以 `${ASK_RATE_PER_MINUTE:-10}` 傳入，`.env.example` 列出三個變數。
- 不合法的值讓 nginx 啟動失敗（`nginx: [emerg] invalid rate ...`），不會變成「沒有限流」：速率與連線數為 0、非數字、空字串；burst 為負數、非數字、空字串。burst 0 是合法的（不允許突發，照速率放行）。容器測試涵蓋。
- 每日上限 `DAILY_QUESTION_LIMIT` 在後端（D3），兩者分開：nginx 管每個 IP 的頻率，後端管全站每日總量。

### D7. nginx 行為以容器測試驗證
`frontend/nginx-tests/`：用 Python 標準函式庫（`unittest`、`urllib`、`subprocess`）啟動兩個容器，放在同一個 Docker network：
- 待測 nginx：`nginx:1.27-alpine` 掛上 repo 的 `nginx.conf` 與一個假的 `index.html`。
- 假 backend：名稱為 `backend` 的 nginx，對任何請求回 200 JSON 並寫 access log；測試讀它的 log 判斷「後端有沒有收到」。

測試涵蓋：白名單與 404、20 次連續提問的 6 通過 14 被擋、429 的 JSON body 與 `Retry-After`、413、不同來源 IP 互不影響（在同一個 Docker network 開第二個 client 容器）、環境變數改變限流數值（例如 burst 2 時只放行 3 次）、不合法的值讓 nginx 啟動失敗。待測 nginx 掛上 `frontend/nginx/default.conf.template`，與正式 image 走同一個模板流程。不呼叫 Bedrock、不需要資料庫。CI 的 frontend job 加一個步驟執行。

## Risks / Trade-offs

- [多人共用同一個 IP（公司、學校 NAT）互相影響] → Demo 情境可接受；429 訊息說明稍後再試
- [每日上限被惡意用光，正常面試官無法使用] → 告警通知（`observe-with-grafana`）；管理者可調高上限或重啟
- [新增公開 API 忘了加進白名單，前端呼叫得到 404] → 本機 compose 也經過同一份 nginx 設定，開發時就會發現；nginx 測試的白名單清單也要一起更新
- [限流數值不合實際] → 評估與實測後調整，集中在一處設定
- [容器測試在 CI 變慢或不穩定] → 只用 alpine image、無外部依賴；每個測試前重啟待測 nginx 以清空限流計數
