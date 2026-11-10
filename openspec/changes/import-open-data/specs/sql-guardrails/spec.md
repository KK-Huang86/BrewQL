## MODIFIED Requirements

### Requirement: 資料表白名單
系統 MUST 只允許查詢設定的白名單資料表與 view（不分大小寫），CTE 定義的名稱 SHALL 被允許。白名單 SHALL 包含公開資料表 `district_population` 與 `universities`。白名單外的資料表、系統目錄、非 `public` schema MUST 被拒絕，包含子查詢中的情況；錯誤訊息 SHALL 列出可用的資料表。

#### Scenario: 系統資料表
- **WHEN** SQL 為 `SELECT * FROM pg_shadow` 或 `SELECT * FROM pg_catalog.pg_user`
- **THEN** 驗證失敗，訊息列出可用資料表

#### Scenario: 子查詢中的未授權資料表
- **WHEN** SQL 為 `SELECT name FROM cafes WHERE id IN (SELECT id FROM secret_table)`
- **THEN** 驗證失敗

#### Scenario: CTE 名稱與大小寫
- **WHEN** SQL 為 `WITH t AS (SELECT city FROM CAFES) SELECT city FROM t`
- **THEN** 驗證通過

#### Scenario: 公開資料表
- **WHEN** SQL 為 `SELECT c.district, count(*) FROM cafes c JOIN district_population p USING (city, district) GROUP BY 1`
- **THEN** 驗證通過
