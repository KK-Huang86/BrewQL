## Why

先打通一條最細但完整的路徑：營運人員在瀏覽器用中文問一個簡單問題，系統透過 Amazon Bedrock 產生 SQL、在唯讀資料庫上執行，畫面顯示結果表格。這是 tracer bullet：越早確認 Bedrock、資料庫、API、前端能串起來，後面每個 ticket 都只是在這條路徑上加深一個行為。

## What Changes

- Demo 資料庫：只建 `cafes` 資料表（沿用 Find Coffee 結構，加上 `city`、`district`）與約 200 家示範咖啡店；唯讀角色 `genbi_reader`
- 後端：`GET /health`、`POST /api/ask`；Bedrock Claude 依固定的 schema 說明、以結構化輸出（JSON schema）回傳 SQL；最基本的防護（只允許單一 SELECT、以唯讀角色在 read-only transaction 執行）
- 前端：問題輸入框、處理中狀態、結果表格、錯誤訊息
- `docker compose up` 一行啟動 db、backend、frontend
- smoke 腳本：在終端機直接呼叫 Bedrock 看產生的 SQL
- CI：backend lint + test、frontend build + test、spec 結構檢查

### Non-goals（由後續 ticket 加入）

完整四層防護、拒答與反問、自動修正、行為資料與圖表、評估、RAG、SQL 編輯、SSE、部署。

## Capabilities

### New Capabilities

- `query-pipeline`: 中文問題 → SQL → 執行 → 結果的核心流程。
- `sql-guardrails`: SQL 執行前後的安全限制（本 ticket 只含單一 SELECT 與唯讀執行）。
- `query-api`: 前端使用的 HTTP API。
- `query-web-ui`: 營運人員使用的網頁。
- `demo-dataset`: Demo 用資料庫與模擬資料。
- `project-ci`: 自動化檢查（lint、測試、spec 一致性）。

### Modified Capabilities

（無）

## Impact

- 新增：`backend/`、`frontend/`、`db/init/`、`docker-compose.yml`、`.env.example`、`.github/workflows/`、`README.md`
- 外部依賴：Amazon Bedrock（需先開通 Claude 模型權限）、PostgreSQL 16 + pgvector image
- 先前已寫的 backend 與 db 初稿：只取本 ticket 需要的部分，其餘留給後續 ticket 重新驗證
