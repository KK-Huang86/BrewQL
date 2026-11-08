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
