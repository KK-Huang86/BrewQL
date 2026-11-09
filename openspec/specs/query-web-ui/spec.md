# query-web-ui Specification

## Purpose
提供營運人員用中文提問並查看結果的網頁介面：顯示實際執行的 SQL 與結果表格，並依錯誤類型區分一般錯誤與安全防護攔截。

## Requirements

### Requirement: 提問與送出控制
介面 SHALL 提供問題輸入框與送出按鈕（Enter 也可送出）。空白問題 MUST NOT 送出；處理中 MUST NOT 送出第二個請求，並 SHALL 顯示處理中狀態。

#### Scenario: 正常送出
- **WHEN** 輸入問題後按送出
- **THEN** 呼叫一次 `POST /api/ask`，畫面顯示處理中

#### Scenario: 空白問題
- **WHEN** 輸入框只有空白時按送出
- **THEN** 不呼叫 API

#### Scenario: 重複送出
- **WHEN** 處理中再次按送出
- **THEN** 不發出第二個請求

### Requirement: 結果表格
`status=ok` 時，介面 SHALL 以表格顯示所有欄位與資料列；沒有資料時 SHALL 顯示「查無資料」。

#### Scenario: 顯示表格
- **WHEN** 回應含 2 欄 3 列
- **THEN** 畫面顯示 2 欄 3 列的表格

#### Scenario: 空結果
- **WHEN** 回應 `rows` 為空
- **THEN** 顯示「查無資料」

### Requirement: 錯誤顯示
`status=error`、網路錯誤或非 200 回應時，介面 SHALL 顯示錯誤訊息，並恢復可再次送出的狀態。

#### Scenario: SQL 被拒絕
- **WHEN** 回應為 `status=error`
- **THEN** 顯示 `message`，不顯示表格

#### Scenario: 後端無法連線
- **WHEN** 請求因網路錯誤失敗
- **THEN** 顯示錯誤訊息，送出按鈕恢復可用

### Requirement: 顯示防護拒絕原因
當 SQL 被防護拒絕時，介面 SHALL 顯示被拒絕的原因與被拒絕的 SQL，樣式 SHALL 與一般錯誤（網路、伺服器）可區分。

#### Scenario: 被擋下的 SQL
- **WHEN** 回應為 `status=error`，原因為不允許查詢的資料表
- **THEN** 畫面顯示原因與該 SQL，樣式標示為「安全防護」

### Requirement: 顯示拒答與反問
`status=refused` 與 `status=clarify` 時，介面 SHALL 顯示 `message`，兩者與錯誤的樣式 MUST 可區分，且不顯示表格。拒答時 SHALL 標示來源（輸入防護或模型）。反問時 SHALL 讓使用者能直接修改原問題再送出。

#### Scenario: 輸入防護拒答
- **WHEN** 回應為 `status=refused`、`refusal_source=input_guardrail`
- **THEN** 顯示拒答原因並標示「輸入防護」

#### Scenario: 反問
- **WHEN** 回應為 `status=clarify`
- **THEN** 顯示反問內容，輸入框保留原問題供修改

### Requirement: 顯示修正次數
回應的 `attempts` 大於 1 時，介面 SHALL 顯示「經過 N 次修正」（N = attempts − 1）。

#### Scenario: 經過修正
- **WHEN** 回應 `status=ok`、`attempts=3`
- **THEN** 顯示「經過 2 次修正」

#### Scenario: 一次成功
- **WHEN** 回應 `attempts=1`
- **THEN** 不顯示修正次數

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
