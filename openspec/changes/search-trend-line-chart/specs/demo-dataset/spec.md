## ADDED Requirements

### Requirement: 模擬使用者與搜尋紀錄
資料庫 SHALL 包含 `users`（2,000 位，`member_type`、`status`、`created_at`）與 `search_logs`（約 50,000 筆，涵蓋最近 6 個月，含 `query_text`、`city`、`district`、JSONB `filters`、`result_count`、`created_at`）。`users` MUST NOT 含任何 LINE 識別欄位。資料 SHALL 使用固定亂數種子。

#### Scenario: 規模
- **WHEN** 計算 `users` 與 `search_logs` 筆數
- **THEN** 分別為 2,000 與約 50,000

#### Scenario: 無 LINE 識別欄位
- **WHEN** 查詢 `users` 欄位清單
- **THEN** 沒有 `line_user_id` 或其他可識別真人的欄位

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
