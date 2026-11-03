## 1. 結構化輸出與模型拒答

- [ ] 1.1 測試 + 實作：JSON schema 擴充為 sql／refuse／clarify，類型與欄位不一致回 error；驗證：測試由紅轉綠
- [ ] 1.2 測試 + 實作：Bedrock 結束原因 refusal 轉拒答（`refusal_source=model`）；驗證：以假 SDK client 的測試由紅轉綠（已有初稿）
- [ ] 1.3 更新 system prompt 說明拒答與反問規則；驗證：涵蓋修改資料、預測、模糊三類
- [ ] 1.4 測試 + 實作：流程與 API 回傳 `refused`、`clarify` 且不執行查詢；驗證：測試由紅轉綠（已有初稿）

## 2. 輸入防護

- [ ] 2.1 Terraform 建立 Bedrock Guardrail（prompt attack、無關話題、拒絕訊息）與發布版本，加入 Terraform CI；驗證：`terraform validate` 通過、`apply` 後輸出 ID 與版本
- [ ] 2.2 測試 + 實作：輸入檢查（攔下時不呼叫模型、通過時繼續、未設定時跳過並警告、呼叫失敗 fail closed），以假 client 測試；驗證：測試由紅轉綠
- [ ] 2.3 呼叫 log 記錄 Guardrail 結果與耗時；驗證：以 caplog 的測試綠燈

## 3. 前端

- [ ] 3.1 測試 + 實作：拒答與反問的樣式、拒答來源標示、反問時保留原問題；驗證：測試由紅轉綠

## 4. 端到端驗證

- [ ] 4.1 以真實 Bedrock 在瀏覽器問：prompt injection、「幫我寫一首詩」、「下個月會有幾位新會員？」、「最近熱門的店」、「台北市有幾家咖啡店？」；驗證：記錄每題的 status、refusal_source 與耗時
