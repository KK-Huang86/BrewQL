## ADDED Requirements

### Requirement: 瀏覽與收藏題
黃金測試集 SHALL 加入至少 4 題涉及瀏覽、收藏或社群評分的題目，至少 1 題需要 JOIN 或兩張表（收藏轉換率）、1 題使用 `v_cafe_profile`、1 題涉及「活躍使用者」定義。完成後的完整評估結果 SHALL 記入評估紀錄，標示為加入 RAG 前的基準。

#### Scenario: 題目可執行
- **WHEN** 以試跑模式執行評估
- **THEN** 新增題目的參考 SQL 都可執行

#### Scenario: 題目組成
- **WHEN** 檢查黃金測試集
- **THEN** 至少 4 題查詢 `cafe_views`、`favorites`、`cafe_nomad_cache` 或 `v_cafe_profile`，其中至少 1 題同時用到 `cafe_views` 與 `favorites`
