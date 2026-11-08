## ADDED Requirements

### Requirement: 回應包含圖表設定
`/api/ask` 回應 SHALL 包含 `chart` 欄位：`status=ok` 時依結果形狀決定（見 result-visualization），其他狀態為 `null`。

#### Scenario: 日期與數值
- **WHEN** 問題的結果為月份與搜尋數
- **THEN** 回應的 `chart` 為 `{type: line, x_key, y_key}`

#### Scenario: 非成功回應
- **WHEN** 回應為 `refused`、`clarify` 或 `error`
- **THEN** `chart` 為 `null`
