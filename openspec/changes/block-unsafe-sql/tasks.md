## 1. 靜態驗證（每組先寫測試、確認紅燈、再實作）

- [x] 1.1 CTE 內資料修改、SELECT INTO、GRANT、COPY；驗證：測試由紅轉綠（ticket 1 已實作走訪整棵語法樹；本 ticket 只補 COPY 測試，直接綠燈）
- [x] 1.2 資料表白名單、CTE 名稱、大小寫、系統資料表、非 public schema、子查詢；驗證：測試由紅轉綠（另補：CTE 名稱依作用範圍判斷，範圍外的同名資料表仍被擋）
- [x] 1.3 封鎖欄位（引號、大小寫）、危險函式（含 FROM 中的 dblink）；驗證：測試由紅轉綠（已知缺口：`SELECT *` 不會展開欄位，目前 `cafes` 沒有封鎖欄位；加入含 `line_user_id` 的資料表前需改用 view 或展開 `*`）
- [x] 1.4 LIMIT 三種情況與上限 ≤ 0；驗證：測試由紅轉綠（另含 LIMIT ALL、非常數 LIMIT、FETCH FIRST、UNION；回傳的 SQL 改為 sqlglot 重新產生的實際執行版本）

## 2. 執行限制

- [x] 2.1 整合測試 + 實作：`SET LOCAL statement_timeout`、角色預設 timeout，`pg_sleep` 逾時被中止；驗證：測試由紅轉綠（角色預設 5s 在 ticket 1 已設定，本 ticket 補測試；每查詢預設 5000ms，≤ 0 視為設定錯誤，因為 Postgres 的 0 代表不限時）

## 3. API 與畫面

- [ ] 3.1 測試 + 實作：回應加入 `error_kind`（guardrail / query / generation）；驗證：API 測試由紅轉綠
- [ ] 3.2 測試 + 實作：畫面依 `error_kind=guardrail` 顯示原因與 SQL、樣式不同；驗證：前端測試由紅轉綠

## 4. 端到端驗證

- [ ] 4.1 端到端測試（以假的模型回傳惡意 SQL，走真實 API 與資料庫）：刪除、DROP、系統資料表、LINE ID、pg_sleep；驗證：資料筆數不變、回應不含禁止內容
- [ ] 4.2 在瀏覽器以真實 Bedrock 問「刪除所有咖啡店資料」與 prompt injection 問題；驗證：記錄模型產生的 SQL 與被擋下的原因
