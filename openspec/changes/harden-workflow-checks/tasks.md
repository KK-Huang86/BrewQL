## 1. CI 檢查

- [x] 1.1 `spec_check.py` 一個有程式碼的 PR 只動一個 change（D1）；驗證：先寫三個情境的測試紅燈，再綠燈

## 2. 突變工具

- [x] 2.1 `db/checks/mutate.sh`（D5）；驗證：先寫 `tools/test_mutate.py`（以假的 `$PSQL` 檢查送出的指令順序與兩種結果）紅燈，再綠燈；對 Demo 資料庫實跑一次 08 的突變

## 3. 規則文件

- [ ] 3.1 新增 `CODING_STANDARDS.md`，從 CLAUDE.md 搬移 TDD、資料操作穩健性、PR 前 spec 一致性檢查（D2～D4）；驗證：搬移前後逐段比對，只有 D3、D4 兩處修改
- [ ] 3.2 CLAUDE.md 只留 D2 列出的內容與導覽，指令區補評估 dry-run 對測試資料庫、測試路徑、`mutate.sh`；驗證：CLAUDE.md 行數下降，指令實際執行一次
