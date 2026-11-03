## Purpose

確保任何由 LLM 產生或使用者提供的 SQL，都只能以唯讀方式查詢允許的資料，不能修改資料或拖垮資料庫。

## ADDED Requirements

### Requirement: 只允許單一 SELECT
系統 MUST 拒絕任何不是單一 SELECT 查詢（含 UNION）的 SQL，包括寫入、刪除、DDL 與多個敘述。被拒絕的 SQL MUST NOT 送到資料庫，並 SHALL 回傳說明原因的中文訊息。

#### Scenario: 合法 SELECT
- **WHEN** SQL 為 `SELECT name FROM cafes`
- **THEN** 驗證通過

#### Scenario: 刪除語句
- **WHEN** SQL 為 `DELETE FROM cafes`
- **THEN** 驗證失敗，資料庫未收到查詢

#### Scenario: 多個敘述
- **WHEN** SQL 為 `SELECT 1; DELETE FROM cafes`
- **THEN** 驗證失敗

#### Scenario: 空白或亂碼
- **WHEN** SQL 為空白或無法解析
- **THEN** 驗證失敗

### Requirement: 唯讀執行
API MUST 以只有 SELECT 權限的唯讀角色連線資料庫，每次查詢 MUST 在 read-only transaction 中執行。即使 SQL 驗證被繞過，資料庫 MUST 拒絕寫入。

#### Scenario: 唯讀角色無法寫入
- **WHEN** 以 API 使用的角色直接執行 `DELETE FROM cafes`
- **THEN** 資料庫拒絕，筆數不變

#### Scenario: 空結果仍有欄位名稱
- **WHEN** 查詢沒有符合的資料
- **THEN** 回傳空的資料列與正確的欄位名稱
