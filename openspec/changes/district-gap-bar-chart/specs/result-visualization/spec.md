## ADDED Requirements

### Requirement: 長條圖判斷
結果為兩欄、第一欄全為文字（不含 NULL）、第二欄為數值、且不超過 30 列時，系統 SHALL 回傳 `{type: bar, x_key, y_key}`；超過 30 列 SHALL 回傳 `table`。第一欄全為時間格式文字（`YYYY-MM`、`YYYY-MM-DD`）時折線圖優先。Decimal SHALL 視為數值，布林不算；第二欄的 NULL 與折線圖相同處理（忽略，全為 NULL 回傳 `table`）。

#### Scenario: 行政區比較
- **WHEN** 欄位為 `district, n`，資料為 `[["內湖區", 30], ["大安區", 20]]`
- **THEN** 回傳 `{type: bar, x_key: district, y_key: n}`

#### Scenario: 剛好 30 類
- **WHEN** 兩欄結果有 30 列
- **THEN** 回傳 `bar`

#### Scenario: 31 類
- **WHEN** 兩欄結果有 31 列
- **THEN** 回傳 `table`

#### Scenario: 月份文字仍是折線圖
- **WHEN** 第一欄為 `2026-05`、`2026-06`
- **THEN** 回傳 `line`

#### Scenario: 類別含 NULL
- **WHEN** 資料為 `[["內湖區", 3], [null, 2]]`
- **THEN** 回傳 `table`

#### Scenario: 第二欄為文字
- **WHEN** 資料為 `[["a", "x"]]`
- **THEN** 回傳 `table`

### Requirement: 數字卡判斷
結果為單列單欄且值為數值（含 Decimal、不含布林）時，系統 SHALL 回傳 `{type: number, value_key}`；值為 NULL 或非數值時 SHALL 回傳 `table`。

#### Scenario: 單一數值
- **WHEN** 欄位為 `count`，資料為 `[[42]]`
- **THEN** 回傳 `{type: number, value_key: count}`

#### Scenario: 單一 NULL
- **WHEN** 資料為 `[[null]]`
- **THEN** 回傳 `table`

#### Scenario: 單一 Decimal
- **WHEN** 欄位為 `avg`，資料為 `[[Decimal("4.25")]]`
- **THEN** 回傳 `{type: number, value_key: avg}`

#### Scenario: 單一布林
- **WHEN** 資料為 `[[true]]`
- **THEN** 回傳 `table`
