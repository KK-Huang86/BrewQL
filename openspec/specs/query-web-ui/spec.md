# query-web-ui Specification

## Purpose
提供營運人員用中文提問並查看結果的網頁介面。

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
