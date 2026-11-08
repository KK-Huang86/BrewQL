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
