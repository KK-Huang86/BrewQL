## ADDED Requirements

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
