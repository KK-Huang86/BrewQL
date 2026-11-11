## MODIFIED Requirements

### Requirement: 資料表白名單
系統 MUST 只允許查詢設定的白名單資料表與 view（不分大小寫），CTE 定義的名稱 SHALL 被允許。白名單 SHALL 包含公開資料表 `district_population`、`universities`、`youbike_stations`、`mrt_stations`，以及距離 view `v_cafe_transit`。白名單外的資料表、系統目錄、非 `public` schema MUST 被拒絕，包含子查詢中的情況；錯誤訊息 SHALL 列出可用的資料表。

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

#### Scenario: 交通公開資料表
- **WHEN** SQL 為 `SELECT district, count(*) FROM youbike_stations GROUP BY 1 UNION ALL SELECT district, count(*) FROM mrt_stations GROUP BY 1`
- **THEN** 驗證通過

#### Scenario: 距離 view
- **WHEN** SQL 為 `SELECT c.name FROM cafes c JOIN v_cafe_transit t ON t.cafe_id = c.id WHERE t.mrt_distance_m <= 400`
- **THEN** 驗證通過

### Requirement: 敏感欄位與危險函式
系統 MUST 拒絕引用封鎖欄位（至少 `line_user_id`，不分大小寫，含加引號）的查詢，並 MUST 拒絕延遲執行、讀取檔案、連線外部資料庫或讀寫設定的函式（至少 `pg_sleep`、`pg_read_file`、`dblink`、`set_config`、`current_setting`），包含出現在 FROM 中的情況。距離 view 內部使用的 `distance_m` 函式 MUST 被拒絕：距離問題一律查 `v_cafe_transit`，模型不直接計算距離。

#### Scenario: LINE ID
- **WHEN** SQL 為 `SELECT "LINE_USER_ID" FROM cafes`
- **THEN** 驗證失敗

#### Scenario: pg_sleep
- **WHEN** SQL 為 `SELECT pg_sleep(10) FROM cafes`
- **THEN** 驗證失敗

#### Scenario: FROM 中的 dblink
- **WHEN** SQL 為 `SELECT * FROM dblink('host=x', 'select 1') AS t(a int)`
- **THEN** 驗證失敗

#### Scenario: 直接呼叫距離函式
- **WHEN** SQL 為 `SELECT name FROM cafes WHERE distance_m(lat, lng, 25.0478, 121.517) < 400`
- **THEN** 驗證失敗；查詢 `v_cafe_transit` 的 SQL 照常通過（view 內部的函式不經過防護解析）
