## 1. 資料庫

- [ ] 1.1 稽核資料表與 `genbi_audit_writer` 角色；驗證：整合測試確認寫入角色讀不到 `cafes`、查詢角色改不了稽核表

## 2. 後端

- [ ] 2.1 測試 + 實作：流程結束後寫入稽核紀錄（成功、攔截、拒答、Bedrock 失敗）；驗證：測試由紅轉綠
- [ ] 2.2 測試 + 實作：稽核寫入失敗仍回應使用者並記錄錯誤；驗證：測試由紅轉綠
- [ ] 2.3 測試 + 實作：每次提問輸出一行 JSON 稽核 log（含 `event: ask_audit`，DB 失敗時仍輸出）；驗證：測試由紅轉綠
- [ ] 2.4 測試 + 實作：`GET /api/audit` 回傳最近紀錄（唯讀、有筆數上限）；驗證：測試由紅轉綠

## 3. 前端

- [ ] 3.1 測試 + 實作：提問紀錄頁；驗證：測試由紅轉綠

## 4. CloudWatch（部署後）

- [ ] 4.1 Terraform：CloudWatch log group（保存 30 天）、EC2 role 只允許 `logs:CreateLogStream`、`logs:PutLogEvents`；驗證：`terraform plan` 無刪除權限
- [ ] 4.2 部署用 compose 設定 `awslogs` driver；驗證：Logs Insights 以 `event = "ask_audit"` 查到紀錄
