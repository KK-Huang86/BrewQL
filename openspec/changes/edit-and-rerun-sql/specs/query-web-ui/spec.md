## ADDED Requirements

### Requirement: 檢視與修改 SQL
回應含 `sql` 時，介面 SHALL 顯示實際執行的 SQL，使用者 SHALL 能編輯並按「重新執行」呼叫 `POST /api/sql`，以新結果取代畫面上的結果與 SQL。空白 SQL MUST NOT 送出；執行中 MUST NOT 重複送出；失敗時 SHALL 顯示錯誤並保留使用者編輯的內容。

#### Scenario: 重新執行
- **WHEN** 把 `LIMIT 10` 改為 `LIMIT 5` 後按重新執行
- **THEN** 畫面顯示 5 筆結果

#### Scenario: 不安全 SQL
- **WHEN** 改成 `DELETE FROM cafes` 後按重新執行
- **THEN** 顯示安全防護訊息，編輯框保留使用者輸入

#### Scenario: 空白 SQL
- **WHEN** 清空編輯框後按重新執行
- **THEN** 不呼叫 API
