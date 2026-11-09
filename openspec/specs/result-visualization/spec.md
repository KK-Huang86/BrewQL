# result-visualization Specification

## Purpose
依查詢結果的形狀（欄數、型別）由後端自動決定呈現方式（折線圖或表格，之後加入長條圖與數字卡），不呼叫模型、同樣的結果一定得到同樣的圖，讓使用者不必自行選擇圖表即可看懂結果。

## Requirements

### Requirement: 折線圖判斷
結果為兩欄、第一欄全為日期或時間（`date`、`timestamp`，或固定格式文字 `YYYY-MM`、`YYYY-MM-DD`）、第二欄為數值時，系統 SHALL 回傳 `{type: line, x_key, y_key}`；其他情況（空結果、欄數不符、各列欄數不一致、第二欄非數值）SHALL 回傳 `{type: table}`。布林值 MUST NOT 視為數值；第二欄的 NULL SHALL 被忽略，全為 NULL 時回傳 `table`。

#### Scenario: 日期與數值
- **WHEN** 欄位為 `month, searches`，第一欄為日期
- **THEN** 回傳 `{type: line, x_key: month, y_key: searches}`

#### Scenario: 月份文字
- **WHEN** 第一欄為 `to_char(created_at, 'YYYY-MM')` 產生的 `2026-05`、`2026-06`
- **THEN** 回傳 `line`

#### Scenario: 一般文字
- **WHEN** 第一欄為行政區名稱
- **THEN** 回傳 `table`

#### Scenario: 空結果
- **WHEN** 沒有資料列
- **THEN** 回傳 `table`

#### Scenario: 第二欄為布林
- **WHEN** 資料為 `[[2026-01-01, true]]`
- **THEN** 回傳 `table`

#### Scenario: 部分 NULL
- **WHEN** 資料為 `[[2026-01-01, 3], [2026-01-02, null]]`
- **THEN** 回傳 `line`

#### Scenario: 欄數不一致
- **WHEN** 欄位為兩個，但某列只有一個值
- **THEN** 回傳 `table`

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

### Requirement: 比較題的回傳欄位
送給模型的資料表說明 SHALL 要求比較或排名題只回傳一個類別欄與一個主要指標欄（問題要求更多欄位時除外），讓結果能畫成長條圖。

#### Scenario: 落空率比較
- **WHEN** 使用者問「哪些行政區最常搜尋不到結果？」
- **THEN** 資料表說明包含「只回傳一個類別欄與一個主要指標欄」的指示
