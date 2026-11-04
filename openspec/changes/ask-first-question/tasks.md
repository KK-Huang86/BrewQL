> TDD：每組先寫測試並確認紅燈，再實作到綠燈。標「已有初稿」者需對照 spec 驗證後才能勾選。

## 1. Demo 資料庫

- [x] 1.1 撰寫 `cafes` schema 與約 200 家示範咖啡店（固定種子、台北市與新北市至少 8 區）；驗證：在全新 Postgres 執行成功，分布檢查查詢符合 spec（已有初稿）
- [x] 1.2 建立唯讀角色 `genbi_reader`（只授權 `cafes` SELECT、預設唯讀）；驗證：以該角色執行 `DELETE FROM cafes` 被拒（已有初稿）
- [x] 1.3 compose 加入 db（pgvector image、init 掛載、健康檢查、127.0.0.1、必填密碼）與 `.env.example`；驗證：缺少密碼時啟動失敗並指出變數

## 2. SQL 防護（最小版）

- [x] 2.1 測試 + 實作：只允許單一 SELECT（含 UNION、結尾分號），拒絕寫入、DDL、多敘述、空白、亂碼；驗證：測試由紅轉綠（已有初稿）
- [x] 2.2 測試 + 實作：資料庫執行器（read-only transaction、prepared statement 取欄位、資料庫錯誤轉為查詢錯誤）；驗證：整合測試確認唯讀角色寫入被拒、空結果有欄位（已有初稿，測試待補）

## 3. Bedrock 與流程

- [x] 3.1 測試 + 實作：結構化輸出（JSON schema 定義、合法回覆、sql 空白、達到 token 上限）；驗證：測試由紅轉綠（初稿為程式碼區塊解析，需改寫）
- [x] 3.2 撰寫 `cafes` 的 schema 說明作為 system prompt；驗證：欄位與 1.1 一致
- [x] 3.3 測試 + 實作：Bedrock 產生器（以假 SDK client 驗證送出內容、log 含模型 ID 與 token、SDK 例外往外拋、呼叫期間事件迴圈不阻塞）；驗證：測試由紅轉綠（已有初稿）
- [x] 3.4 測試 + 實作：流程（成功、沒有 SQL 回 error、防護拒絕回 error 且未執行、空白與過長問題、服務錯誤往外拋）；驗證：測試由紅轉綠（已有初稿，需刪除本 ticket 不含的重試等邏輯）
- [x] 3.5 smoke 腳本：輸入問題印出 SQL 與 token 數；驗證：Bedrock 開通後實際執行「台北市有幾家咖啡店？」並記錄輸出（帳號尚無法使用 Haiku 5.5，改以 `us.anthropic.claude-haiku-4-5-20251001-v1:0` + `BEDROCK_EFFORT=` 驗證：產生 `SELECT COUNT(*) as cafe_count FROM cafes WHERE city = '台北市'`，input 561 / output 26 tokens）

## 4. API

- [x] 4.1 測試 + 實作：`/health`（外部依賴不可用仍回 ok）、`/api/ask`（成功、日期與 Decimal 序列化、422 三種、防護拒絕回 error、Bedrock 失敗回 5xx）、CORS；驗證：測試由紅轉綠（已有初稿，5xx 與 CORS 測試待補）
- [x] 4.2 backend Dockerfile 並加入 compose（以 `genbi_reader` 連線、本機 AWS 憑證唯讀掛載）；驗證：`docker compose up` 後 `curl localhost:8000/health` 回 ok

## 5. 前端

- [x] 5.1 建立 Vite + React + TypeScript、Vitest、React Testing Library、`/api` dev proxy；驗證：`npm run build`、`npm test` 成功
- [x] 5.2 測試 + 實作：API client（成功、非 200 與網路錯誤轉錯誤訊息）；驗證：測試由紅轉綠
- [x] 5.3 測試 + 實作：頁面（正常送出、空白不送、處理中不重送、表格、查無資料、錯誤後可再送出）；驗證：測試由紅轉綠
- [x] 5.4 frontend Dockerfile（nginx 提供靜態檔並轉發 `/api`）加入 compose；驗證：瀏覽 `http://localhost:8080`

## 6. CI 與文件

- [x] 6.1 GitHub Actions：backend（ruff + pytest + Postgres service 跑整合測試）、frontend（build + test），以 path filter 分開；驗證：push 後綠燈
- [ ] 6.2 spec 一致性檢查 workflow；驗證：測試 PR 確認「只改程式碼」失敗、「程式碼 + openspec」通過
- [ ] 6.3 README：專案定位、架構圖、本機啟動步驟、資料為模擬的說明；驗證：照 README 從零啟動成功

## 7. 端到端驗證

- [ ] 7.1 `docker compose up` 後在瀏覽器問「台北市有幾家咖啡店？」與「大安區評分最高的 5 家店」；驗證：顯示正確表格，記錄 SQL 與耗時
