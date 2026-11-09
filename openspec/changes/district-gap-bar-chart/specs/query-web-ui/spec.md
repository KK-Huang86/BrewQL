## ADDED Requirements

### Requirement: 長條圖與數字卡
`chart.type=bar` 時，介面 SHALL 畫出長條圖（類別依查詢結果的順序）並可展開原始資料；`chart.type=number` 時 SHALL 以大字顯示千分位格式的數字（小數最多 2 位）與欄位名稱。

#### Scenario: 長條圖
- **WHEN** 回應為 `chart={type: bar, x_key: district, y_key: n}`
- **THEN** 顯示長條圖，x 軸為各行政區

#### Scenario: 數字卡
- **WHEN** 回應為 `chart={type: number, value_key: count}`、資料 `[[12345]]`
- **THEN** 顯示「12,345」與標籤「count」

#### Scenario: 數字卡的小數
- **WHEN** 數字卡的值為 `4.256`
- **THEN** 顯示「4.26」

#### Scenario: 圖表提示框的數字
- **WHEN** 滑鼠移到折線圖或長條圖上，值為 `0.5401909`
- **THEN** 提示框顯示「0.54」（與數字卡相同格式）
