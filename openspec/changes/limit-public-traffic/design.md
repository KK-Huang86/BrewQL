## Context

nginx 在前端容器內，同時提供靜態檔與轉發 `/api/`；部署時 EC2 直接對外，前面沒有 CloudFront 或 ALB。後端是單一 uvicorn process。

## Goals / Non-Goals

**Goals:** 單一來源無法把費用或服務打爆；分散來源的濫用也有成本上限；被限流的使用者看得懂原因。

**Non-Goals:** 防禦大規模 DDoS（交給 AWS Shield Standard 的預設保護與關機）。

## Decisions

### D1. 依端點成本分級限流
| 端點 | 每 IP 速率 | burst | 理由 |
|---|---|---|---|
| `/api/ask`、串流端點 | 10 次／分鐘 | 5 | 每次都呼叫 Guardrail 與模型，會花錢 |
| `/api/sql` | 30 次／分鐘 | 10 | 只用資料庫，且有 5 秒逾時與 1000 筆上限 |
| 其他 `/api/` | 60 次／分鐘 | 20 | 便宜的讀取 |
| 靜態檔 | 不限速率 | — | 由同時連線數限制 |

每個 IP 同時連線最多 20；串流端點每個 IP 同時最多 2 條。數值集中寫在 `nginx.conf` 一處，調整時只改一個檔案。

### D2. 429 回應與合約同形
nginx 以 `error_page 429` 回傳 JSON：`{"status":"error","sql":null,"columns":[],"rows":[],"message":"請求太頻繁，請稍後再試","error_kind":null,"refusal_source":null}` 並附 `Retry-After`。前端既有的錯誤路徑會直接顯示 `message`，不需要特別處理格式。

### D3. 全域每日上限放在應用程式
nginx 只能依 IP 計數，擋不住多個 IP 分散提問。後端在呼叫 Guardrail 之前檢查當日（UTC）已處理的提問數，超過 `DAILY_QUESTION_LIMIT`（預設 500）就回 429，不產生任何外部費用。以 Haiku 每題約 US$0.002 估算，上限約等於每天 US$1。
- 計數放在記憶體：單一 process 足夠；重啟會歸零，但重啟本身需要管理者操作，可接受。
- 替代方案：存在資料庫 → 需要可寫入的角色，違反 API 只用 `genbi_reader` 的原則。

### D4. 用 `$binary_remote_addr` 識別來源
EC2 直接對外，連線來源就是真實 IP。若之後前面加上 CloudFront 或 ALB，MUST 改用 `real_ip` 模組並只信任該 proxy 的位址，否則所有人會共用同一個限流額度，或者可以偽造 `X-Forwarded-For` 繞過限流。

### D5. 請求大小與逾時
`client_max_body_size 16k`（問題最多 1000 字，JSON 不會超過）；`client_body_timeout`、`client_header_timeout` 10 秒，降低慢速連線佔住 worker 的風險。

### D6. 內部端點不對外
nginx 只轉發明確列出的 `/api/` 路徑；`/metrics` 不在 `/api/` 之下，不會被轉發。之後若有管理用途的端點（例如稽核查詢），nginx MUST 以 `deny all` 擋下，管理者透過 SSH tunnel 直接連 backend。

## Risks / Trade-offs

- [多人共用同一個 IP（公司、學校 NAT）互相影響] → Demo 情境可接受；429 訊息說明稍後再試
- [每日上限被惡意用光，正常面試官無法使用] → 告警通知（`observe-with-grafana`）；管理者可調高上限或重啟
- [限流數值不合實際] → 評估與實測後調整，集中在一處設定
