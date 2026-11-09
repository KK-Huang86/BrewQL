## ADDED Requirements

### Requirement: 瀏覽與收藏資料表可查詢
SQL 白名單與唯讀角色授權 SHALL 包含 `cafe_nomad_cache`、`cafe_attribute_votes`、`cafe_views`、`favorites`、`v_cafe_profile`；其他防護規則不變。

#### Scenario: 查詢收藏
- **WHEN** SQL 為 `SELECT count(*) FROM favorites`
- **THEN** 防護通過，唯讀角色可以執行

#### Scenario: 白名單外仍被擋
- **WHEN** SQL 為 `SELECT * FROM pg_user`
- **THEN** 防護拒絕
