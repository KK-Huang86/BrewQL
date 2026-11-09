## ADDED Requirements

### Requirement: 完整的 schema 與名詞說明
給模型的說明 SHALL 涵蓋所有白名單資料表與 view 的欄位意義，以及商業名詞定義：工作友善、搜尋落空率、收藏轉換率、活躍使用者（與 `users.status` 區分）、收藏很少／很多、時間用語。說明 SHALL 建議店家屬性與社群評分一起查詢時優先使用 `v_cafe_profile`。

#### Scenario: 名詞定義存在
- **WHEN** 檢查給模型的說明
- **THEN** 包含上述名詞的定義，且收藏轉換率的算法與故事檢查 SQL 一致

#### Scenario: 說明涵蓋白名單
- **WHEN** 比對說明中的資料表與 SQL 白名單
- **THEN** 白名單中每個資料表與 view 都有說明
