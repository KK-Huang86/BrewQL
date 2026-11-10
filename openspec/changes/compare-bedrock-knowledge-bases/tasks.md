## 1. 檢索器介面

- [ ] 1.1 測試 + 重構：把 pgvector 檢索包成檢索器介面，API 預設使用 pgvector，評估可指定檢索器；驗證：既有檢索與評估測試維持綠燈，新增「未指定時用 pgvector」測試由紅轉綠

## 2. Knowledge Bases 實驗資源

- [ ] 2.1 查證 Knowledge Bases 可用的向量儲存與計費，選定最便宜的一個；驗證：選擇與來源記入取捨文件草稿
- [ ] 2.2 Terraform：S3 資料來源（每份文件附 ID、類型 metadata）、向量儲存、Knowledge Base 與 IAM role（實驗標籤、單一檔案）；驗證：使用者 apply 後同步完成，文件數等於知識文件數

## 3. Knowledge Bases 檢索器

- [ ] 3.1 測試 + 實作：Knowledge Bases 檢索器（metadata 對回文件 ID 與類型、三類各前 N 筆、未知文件忽略並警告、API 錯誤處理），以假 client 測試；驗證：測試由紅轉綠

## 4. 比較

- [ ] 4.1 測試 + 實作：評估報告記錄檢索器，比較摘要列出每題檢索結果差異與檢索延遲；驗證：測試由紅轉綠
- [ ] 4.2 以真實 Bedrock 用兩種檢索器跑同一測試集；驗證：比較摘要記入評估紀錄（正確率、檢索差異、延遲、成本）
- [ ] 4.3 使用者 `terraform destroy` 實驗資源；驗證：AWS 上查不到 Knowledge Base 與向量儲存

## 5. 取捨文件

- [ ] 5.1 `docs/aws-managed-alternatives.md`：向量檢索（實測）、監控、部署、流程編排四節，各列自建與託管方案、成本、維運、可攜性與選擇理由；README 加連結；驗證：每節的成本與限制都附來源與查證日期
