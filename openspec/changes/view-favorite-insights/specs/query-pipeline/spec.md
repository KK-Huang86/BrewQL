## ADDED Requirements

### Requirement: 完整的 schema 與名詞說明
給模型的說明 SHALL 涵蓋所有白名單資料表與 view 的欄位意義，以及商業名詞定義：工作友善、搜尋落空率、收藏轉換率、活躍使用者、時間用語。說明 SHALL 建議優先使用 view。

#### Scenario: 名詞定義存在
- **WHEN** 檢查給模型的說明
- **THEN** 包含上述五個名詞的定義，且與故事檢查 SQL 的計算方式一致
