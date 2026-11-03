## ADDED Requirements

### Requirement: 瀏覽、收藏與社群評分
資料庫 SHALL 包含 `cafe_nomad_cache`（約 70% 的店有資料）、`cafe_attribute_votes`、`cafe_views`（約 200,000 筆，`source` 為 search／favorite／rich_menu）、`favorites`（同一使用者對同一店最多一筆），並更新 `cafes` 的 `favorite_count`、`view_count` 使其與明細一致。

#### Scenario: 計數一致
- **WHEN** 比較 `cafes.favorite_count` 與 `favorites` 的實際筆數
- **THEN** 每家店都相同

#### Scenario: 收藏不重複
- **WHEN** 依 `user_id, cafe_id` 分組計算 `favorites`
- **THEN** 每組最多 1 筆

### Requirement: 咖啡店總覽 view
資料庫 SHALL 提供 `v_cafe_profile`（咖啡店欄位 + 社群評分）；沒有社群評分的店 SHALL 仍出現，評分欄為 NULL。`v_daily_activity` SHALL 加入每日瀏覽數與新增收藏數。

#### Scenario: 沒有社群評分的店
- **WHEN** 某店沒有 `cafe_nomad_cache` 資料
- **THEN** 它仍在 `v_cafe_profile` 中，`wifi` 為 NULL

### Requirement: 轉換率與評分落差故事
來源為 `search` 的瀏覽，其收藏轉換率 MUST 高於 `rich_menu`；且 MUST 至少有一家 Google 評分 ≥ 4.7 的店，收藏數低於所有店的中位數。

#### Scenario: 轉換率
- **WHEN** 依瀏覽來源計算收藏轉換率
- **THEN** `search` 高於 `rich_menu`

#### Scenario: 高評分低收藏
- **WHEN** 查詢評分 ≥ 4.7 且收藏數低於中位數的店
- **THEN** 至少有一家
