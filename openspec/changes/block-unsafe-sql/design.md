## Context

ticket 1 已有 sqlglot 驗證與唯讀角色。本 ticket 在同一個模組擴充規則。

## Goals / Non-Goals

**Goals:** 四層防護完整、每條規則都有單元測試、惡意輸入有端到端測試。

**Non-Goals:** 查詢成本估算（EXPLAIN）、列級權限。

## Decisions

### D1. 四層分工
1. 資料庫角色（真正的安全邊界）
2. sqlglot 靜態驗證（提早擋下、提供可讀錯誤，之後讓模型據以修正）
3. 執行限制（LIMIT、timeout、read-only transaction）
4. 欄位與函式封鎖

第 2 層無法涵蓋所有 Postgres 語法，所以第 1 層必須存在；第 1 層錯誤對模型不友善，所以第 2 層也必須存在。

### D2. 走訪整棵語法樹
不只看最外層敘述類型，才能擋下 CTE 內的 DELETE。

### D3. timeout 設兩處
`SET LOCAL statement_timeout` 保證每個查詢都有；角色預設 timeout 保護「繞過 API 直接連線」的情況。

### D4. 回應的 `status=error` 加上 `error_kind`
區分 `guardrail`（被防護擋下）、`query`（資料庫執行錯誤）、`generation`（模型沒產生 SQL），讓前端用不同樣式，也讓之後的評估與重試能依類型處理。

## Risks / Trade-offs

- [sqlglot 解析失敗合法語法] → 視為驗證失敗；ticket 4 會讓模型重寫
- [危險函式清單不完整] → 唯讀角色 + timeout 限制最壞情況
