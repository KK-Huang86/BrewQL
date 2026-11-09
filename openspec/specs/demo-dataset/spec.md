# demo-dataset Specification

## Purpose
提供與 Find Coffee 資料表結構一致、不含任何真實使用者資料的 Demo 資料庫，讓 GenBI 有資料可以查詢。

## Requirements

### Requirement: 一鍵建立資料庫
在空的資料 volume 上執行 `docker compose up` 時，資料庫 SHALL 自動建立 schema、唯讀角色與示範資料。缺少 `POSTGRES_PASSWORD` 或 `GENBI_READER_PASSWORD` 時 MUST 啟動失敗並指出缺少的變數。資料庫 port MUST 只綁定 127.0.0.1。

#### Scenario: 首次啟動
- **WHEN** 已設定 `.env` 並執行 `docker compose up`
- **THEN** 資料庫健康檢查通過，`cafes` 有資料

#### Scenario: 缺少密碼
- **WHEN** 未設定 `GENBI_READER_PASSWORD`
- **THEN** 啟動失敗並指出 `GENBI_READER_PASSWORD`

### Requirement: 咖啡店資料
資料庫 SHALL 包含沿用 Find Coffee 結構的 `cafes`（含 `city`、`district`、`rating`、`limited_time`、`has_socket` 等），約 200 家示範咖啡店，分布於台北市與新北市多個行政區，並使用固定亂數種子。

#### Scenario: 分布
- **WHEN** 依城市與行政區統計 `cafes`
- **THEN** 台北市與新北市都有資料，至少 8 個行政區

#### Scenario: 可重現
- **WHEN** 刪除 volume 後重建
- **THEN** 各行政區咖啡店數量與重建前相同

### Requirement: 模擬使用者與搜尋紀錄
資料庫 SHALL 包含 `users`（2,000 位，`member_type`、`status`、`created_at`）與 `search_logs`（約 50,000 筆，涵蓋最近 6 個月，含 `query_text`、`city`、`district`、JSONB `filters`、`result_count`、`created_at`）。`users` MUST NOT 含任何 LINE 識別欄位。資料 SHALL 使用固定亂數種子；搜尋紀錄的日期 SHALL 以建立資料庫當天為基準往回 6 個月，使「最近半年」的問題永遠有資料，重建時分布形狀相同、只隨建庫日期平移。

#### Scenario: 規模
- **WHEN** 計算 `users` 與 `search_logs` 筆數
- **THEN** 分別為 2,000 與約 50,000

#### Scenario: 無 LINE 識別欄位
- **WHEN** 查詢 `users` 欄位清單
- **THEN** 沒有 `line_user_id` 或其他可識別真人的欄位

#### Scenario: 會員註冊後才搜尋
- **WHEN** 合併 `search_logs` 與 `users`
- **THEN** 沒有任何搜尋早於該會員的 `created_at`

#### Scenario: 日期涵蓋最近半年
- **WHEN** 在建庫當天查詢 `search_logs` 的最早與最晚 `created_at`
- **THEN** 最晚不晚於當天，最早不早於 6 個月前

### Requirement: 每日活動 view
資料庫 SHALL 提供 `v_daily_activity`，從第一筆搜尋日到今天每天一列，含當日搜尋數與新會員數，無活動為 0。

#### Scenario: 日期連續
- **WHEN** 查詢 `v_daily_activity`
- **THEN** 日期沒有缺漏，無活動的欄位為 0

### Requirement: 考試季效應
考試季（5、6、11、12 月）中，`filters` 同時含「不限時」與「插座」條件的搜尋比例 MUST 高於其他月份的平均。

#### Scenario: 考試季比例較高
- **WHEN** 依月份計算工作友善條件的搜尋比例
- **THEN** 考試季月份的平均比例高於非考試季月份

### Requirement: 供給缺口故事
內湖區的搜尋量 MUST 排在所有行政區前 3 名，且其搜尋落空率（`result_count = 0` 的搜尋數 ÷ 該區搜尋數）MUST 是所有行政區中最高。調整行政區分布 MUST NOT 破壞既有故事（考試季效應、註冊後才搜尋、日期範圍），也 MUST NOT 改變 `cafes`。

#### Scenario: 落空率排名
- **WHEN** 依行政區計算搜尋落空率並由高到低排序
- **THEN** 第一名是內湖區

#### Scenario: 搜尋量排名
- **WHEN** 依行政區計算搜尋量並由高到低排序
- **THEN** 內湖區在前 3 名

### Requirement: 瀏覽、收藏與社群評分
資料庫 SHALL 包含以真實 Find Coffee 匯出檔欄位為準的 `cafe_nomad_cache`（約 70% 的店有一列，以 `cafe_id` 對應）、`cafe_attribute_votes`（MUST NOT 含 `user_id`）、`cafe_views`（約 200,000 筆，`source` 為 search／favorite／rich_menu）、`favorites`（同一會員對同一店最多一筆，`source` 為 search 或 rich_menu）。`cafes` SHALL 新增 `favorite_count`、`view_count`，值與明細一致。瀏覽與收藏 MUST 發生在會員註冊之後、建庫日往回 6 個月內；每筆收藏 MUST 有一筆更早、同會員同店同來源的瀏覽。新資料 MUST NOT 改變既有的店家、會員與搜尋紀錄。

#### Scenario: 計數一致
- **WHEN** 比較 `cafes.favorite_count`、`view_count` 與 `favorites`、`cafe_views` 的實際筆數
- **THEN** 每家店都相同

#### Scenario: 收藏不重複
- **WHEN** 依 `user_id, cafe_id` 分組計算 `favorites`
- **THEN** 每組最多 1 筆

#### Scenario: 收藏前有瀏覽
- **WHEN** 檢查每筆收藏
- **THEN** 都有一筆更早、同會員同店同來源的瀏覽

#### Scenario: 投票不含使用者
- **WHEN** 查看 `cafe_attribute_votes` 的欄位
- **THEN** 沒有 `user_id`

### Requirement: 咖啡店總覽 view
資料庫 SHALL 提供 `v_cafe_profile`（咖啡店欄位 + 社群評分與捷運站）；沒有社群評分的店 SHALL 仍出現，評分欄為 NULL。`v_daily_activity` SHALL 加入每日瀏覽數 `views` 與新增收藏數 `new_favorites`，沒有活動為 0。

#### Scenario: 沒有社群評分的店
- **WHEN** 某店沒有 `cafe_nomad_cache` 資料
- **THEN** 它仍在 `v_cafe_profile` 中，`wifi` 為 NULL

#### Scenario: 每日瀏覽與收藏
- **WHEN** 加總 `v_daily_activity` 的 `views` 與 `new_favorites`
- **THEN** 分別等於 `cafe_views` 與 `favorites` 的筆數

### Requirement: 轉換率與評分落差故事
收藏轉換率定義為某入口的收藏數 ÷ 該入口的瀏覽數。`search` 的轉換率 MUST 高於 `rich_menu`；且 MUST 至少有一家 Google 評分 ≥ 4.7 的店，`favorite_count` 低於所有店的中位數。

#### Scenario: 轉換率
- **WHEN** 依入口計算收藏轉換率
- **THEN** `search` 高於 `rich_menu`

#### Scenario: 高評分低收藏
- **WHEN** 查詢評分 ≥ 4.7 且收藏數低於中位數的店
- **THEN** 至少有一家
