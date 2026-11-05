## 1. 結構化輸出與模型拒答

- [x] 1.1 測試 + 實作：JSON schema 擴充為 sql／refuse／clarify，產生 SQL 的介面改回傳三種結果之一；類型與欄位不一致回 error；驗證：測試由紅轉綠
- [x] 1.2 測試 + 實作：Bedrock 結束原因 refusal 轉拒答（`refusal_source=model`）；驗證：以假 SDK client 的測試由紅轉綠
- [x] 1.3 更新 system prompt 說明拒答與反問規則，禁止以必定查不到資料的 SQL 敷衍；驗證：涵蓋修改資料、預測、模糊三類
- [x] 1.4 測試 + 實作：流程與 API 回傳 `refused`、`clarify`（HTTP 200、`sql=null`、`refusal_source`）且不執行查詢；驗證：測試由紅轉綠

  - 真實 Bedrock（Haiku 4.5，smoke 腳本）：刪除資料、pg_shadow、寫詩、預測新會員 → refuse；「最近熱門的店」→ clarify（反問天數與指標）；「台北市有幾家咖啡店？」→ SQL。ticket 2 的空結果敷衍沒有再出現。input tokens 由約 560 增至約 1,100。

## 2. 輸入防護

- [ ] 2.1 Terraform 建立 Bedrock Guardrail（Standard 方案、cross-region、prompt attack、無關話題、拒絕訊息）與發布版本，state 加入 `.gitignore`，CI 每個 PR 執行 `fmt -check` 與 `validate`；驗證：`terraform validate` 通過、`apply` 後輸出 ID 與版本
- [x] 2.2 測試 + 實作：輸入檢查（攔下時不呼叫模型、通過時繼續、未設定時跳過並在啟動時警告、呼叫失敗 fail closed 回 502），以假 client 測試；新增設定同步 `.env.example`；驗證：測試由紅轉綠
- [x] 2.3 測試 + 實作：輸入檢查 log 記錄結果、原因類別與耗時；驗證：以 caplog 的測試由紅轉綠

## 3. 前端

- [ ] 3.1 測試 + 實作：拒答與反問的樣式、拒答來源標示、反問時保留原問題；驗證：測試由紅轉綠

## 4. 端到端驗證

- [ ] 4.1 以真實 Bedrock 在瀏覽器問：中文 prompt injection、「刪除所有咖啡店資料」、「幫我寫一首詩」、「下個月會有幾位新會員？」、「最近熱門的店」、「台北市有幾家咖啡店？」；驗證：記錄每題的 status、refusal_source 與耗時
