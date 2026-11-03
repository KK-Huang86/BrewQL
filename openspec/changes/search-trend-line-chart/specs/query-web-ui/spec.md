## ADDED Requirements

### Requirement: 折線圖
`chart.type=line` 時，介面 SHALL 畫出折線圖，x 軸依時間由舊到新排序，並提供展開原始資料表格的方式。未知的 `chart.type` SHALL 只顯示表格且不出錯。

#### Scenario: 顯示折線圖
- **WHEN** 回應為 `chart={type: line, x_key: month, y_key: searches}`
- **THEN** 顯示折線圖，x 軸由舊到新

#### Scenario: 展開資料
- **WHEN** 顯示折線圖時點選「查看資料」
- **THEN** 顯示完整表格

#### Scenario: 未知類型
- **WHEN** `chart.type` 為 `pie`
- **THEN** 只顯示表格
