## Context

- `/api/ask` 已經有 JSON log 與 Prometheus 指標（`observe-with-grafana`），但兩者刻意不含問題原文與 SQL，無法回頭查某一題。
- `pipeline.AskResult` 只保留最後一次嘗試的 SQL；重試前失敗的 SQL 只出現在 WARNING log。
- API 只用 `genbi_reader` 連資料庫（唯讀、5 秒逾時）；`db/init` 只在資料庫第一次建立時執行。
- nginx 只轉發 `/api/ask`，backend port 只綁 `127.0.0.1`；backend 現在看到的來源 IP 是 nginx 容器。
- Alloy 已經收 backend 的 stdout 送到 Loki；管理者已經在用 Grafana Cloud。

## Goals / Non-Goals

**Goals:** 每次進入 handler 的提問都留下一筆可查詢、角色層級防竄改的紀錄；應用程式之外有第二份紀錄；公開網址沒有讀取紀錄的入口；稽核失敗不影響回答但一定被發現。

**Non-Goals:** 登入與身分、row-level security、自動清除、記錄被 nginx 或每日上限擋下的請求。

## Decisions

### D1. 資料表 `ask_audit`

| 欄位 | 型別 | 說明 |
|---|---|---|
| `request_id` | `UUID PRIMARY KEY` | backend 每個請求產生一次；寫入用 `ON CONFLICT DO NOTHING`，同一筆重送不會重複 |
| `created_at` | `TIMESTAMPTZ NOT NULL DEFAULT now()` | |
| `visitor` | `TEXT` | 來源 IP 的 HMAC（D5）；取不到 IP 時為 NULL |
| `question` | `TEXT NOT NULL` | 去頭尾空白後的問題（最多 `MAX_QUESTION_CHARS` 字，與 API 驗證一致） |
| `sql` | `TEXT` | 最後一次嘗試的 SQL：成功時是實際執行的 SQL（防護加過 `LIMIT`），被防護拒絕時是模型產生的 SQL |
| `failed_attempts` | `JSONB NOT NULL DEFAULT '[]'` | 先前失敗的嘗試：`[{error_kind, reason, sql}]` |
| `status` | `TEXT NOT NULL` | `ok`、`clarify`、`refused`、`error` |
| `refusal_source`、`error_kind` | `TEXT` | 與 API 回應相同；5xx 為 `unavailable_guardrail`、`unavailable_db`、`unavailable_model` |
| `guardrail_reasons` | `TEXT[] NOT NULL DEFAULT '{}'` | 輸入防護的攔截原因 |
| `model_id`、`input_tokens`、`output_tokens` | | 與指標相同來源（`AskUsage`） |
| `guardrail_units`、`estimated_cost_usd` | | `estimated_cost_usd` 為 NULL 代表單價未知（`pricing.cost_usd`） |
| `elapsed_ms`、`row_count` | `INTEGER` | `row_count` 只有成功時有值；不保存查詢結果本身 |

- 不存結果資料：結果可以用 SQL 重現，存下來只會讓表變大。
- 索引：`created_at DESC`（dashboard 與管理者查最近紀錄）。

### D2. 角色：寫入與查詢分開
- `genbi_audit_writer`：`INSERT, SELECT ON ask_audit`，沒有 UPDATE、DELETE、TRUNCATE，沒有任何業務資料表的權限；`statement_timeout = '2s'`、`CONNECTION LIMIT 5`。
- `genbi_reader` 不授權 `ask_audit`：即使 SQL 防護被繞過，模型產生的 SQL 也讀不到其他訪客的問題。
- 給 SELECT 是為了 `ON CONFLICT` 與管理者用 psql 查詢；竄改需要 UPDATE／DELETE，只有資料庫擁有者能做，而擁有者帳號不進 API。
- 角色與資料表放在新的 `db/init/04_audit.sh`；密碼 `GENBI_AUDIT_WRITER_PASSWORD` 與 reader 一樣由 compose 傳入，backend 以 `AUDIT_DATABASE_URL` 連線（獨立的 asyncpg pool，`max_size=2`）。

### D3. 什麼時候寫
handler 在回應前記錄，涵蓋 pipeline 回傳的所有結果與 5xx（`_outage`）。被每日上限擋下（429）與 request 驗證失敗（422）不記錄：沒有進入 pipeline。

順序：先輸出 `ask_audit` JSON log（D6），再寫 DB；DB 寫入以 `asyncio.wait_for` 限 2 秒、不重試。這樣 DB 失敗時第二份紀錄已經存在，錯誤 log 帶 `request_id` 可以對回去。
- 替代方案：FastAPI `BackgroundTasks` 在回應後才寫 → 不增加延遲，但 process 在回應後結束會遺失紀錄，測試也較難確定寫入時機。單筆 INSERT 約數毫秒，回應前寫入較簡單。

### D4. 稽核失敗不中斷回答（資料操作穩健性）
- 原子性與 rollback：單筆 INSERT，失敗即沒有這一筆，不需要補償；JSON log 已輸出，作為補資料的來源。
- 冪等：`request_id` 主鍵 + `ON CONFLICT DO NOTHING`。
- 逾時與重試：2 秒、不重試（重試會拖慢回答，而且失敗通常是資料庫掛了）。
- 錯誤不可吞：ERROR log（含 `request_id`、例外類型，不含問題原文）、`brewql_audit_write_failures_total` 加 1、Grafana 告警（5 分鐘內大於 0）。指標從 0 開始（`observe-with-grafana` 的 `increase()` 教訓）。
- 啟動時沒設定 `AUDIT_DATABASE_URL` 或 `AUDIT_IP_HMAC_KEY` → 啟動失敗：稽核是公開前的必要條件，不能靜默關掉。單元測試以 fake 注入 `create_app`，不受影響。

### D5. 訪客識別：IP 的 HMAC
- `visitor = HMAC-SHA256(AUDIT_IP_HMAC_KEY, ip)` 的 hex。看得出同一來源問了哪些問題，但不存可反查的 IP；金鑰只在 `.env`，至少 32 字元。
- 來源 IP：nginx 以 `proxy_set_header X-Real-IP $remote_addr` 覆寫（使用者自己送的 `X-Real-IP` 會被蓋掉）；backend 讀 `X-Real-IP`，沒有時用連線來源（管理者直連 `127.0.0.1:8000`）。backend 只能從 nginx 或本機連到，所以可以信任這個 header。
- 不用 `X-Forwarded-For`：nginx 用 `$proxy_add_x_forwarded_for` 是附加在使用者送的值後面，第一個值可以偽造。

### D6. 第二份紀錄：`ask_audit` JSON log → Loki
- 一行 INFO log，`logger=app.audit`、`message=ask_audit`、`event=ask_audit`，欄位與 DB 相同（`created_at` 改用 log 的 `time`）。
- 修改 `observability` 的 JSON log 規則：問題原文只允許出現在這一種 log。其他 log 仍不含問題原文。
- Alloy 不需修改：backend 的 stdout 已經送到 Loki；`event` 不轉成 Loki 標籤（避免增加 stream），查詢用 `| json | event="ask_audit"`。
- Grafana Cloud 的 Alloy token 只有寫入權限（`metrics:write`、`logs:write`），backend 主機被入侵也刪不了 Loki 裡的紀錄。保存期限依 Grafana Cloud 方案（免費方案的期限在實作時查證並記入 README）；永久紀錄在 DB。

### D7. 管理者查看：Grafana 稽核 dashboard
- 新的 `observability/dashboards/brewql-audit.json`：Loki 表格面板（時間、visitor、status、問題、SQL、錯誤種類），可依 `status`、`visitor` 篩選；另一個面板是重複提問數（同一個問題文字出現多次）與每題 input token，供 prompt caching 評估。
- 不做 `/api/audit` 與前端紀錄頁：公開網址完全沒有讀取紀錄的入口，也少一個要保護的 API。
- 需要完整歷史時，管理者以 SSH tunnel 連資料庫，用 `genbi_audit_writer` 或擁有者帳號以 psql 查詢（README 說明）。

### D8. `AskResult.failed_attempts`
pipeline 在重試時把每次 `FailedAttempt` 放進 `AskResult.failed_attempts`（`compare=False`，與 `usage` 一樣不影響結果比較）。API 回應不變。

### D9. 提問畫面提示
提問框下方固定顯示「提問內容會被記錄以供稽核，請勿輸入個人資料」。

## Risks / Trade-offs

- [問題原文進入 Loki] → 只限 `ask_audit` 一種 log；Grafana Cloud 只有管理者能登入；提問畫面請使用者不要輸入個人資料。
- [回應前寫 DB 增加延遲] → 單筆 INSERT，2 秒上限；失敗只記錄不重試。
- [啟動時強制需要稽核設定] → 本機 `.env` 要新增兩個變數；`.env.example` 與 README 說明。
- [db/init 只在第一次執行] → 既有本機資料庫要 `docker compose down -v`；部署時是新資料庫，不受影響。之後若需要不刪資料的升級，再引入 migration 工具。
- [HMAC 金鑰外洩] → 可以用常見 IP 反推 visitor；金鑰只在 `.env`，更換金鑰後新舊紀錄的 visitor 無法對應（可接受）。
