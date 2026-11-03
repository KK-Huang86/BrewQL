## ADDED Requirements

### Requirement: 串流提問端點
系統 SHALL 提供以 SSE 回傳的串流提問端點，輸入驗證與 `/api/ask` 相同。依序推送 `step` 事件，最後推送一個 `result` 事件（內容與 `/api/ask` 回應相同）；發生服務錯誤時推送 `error` 事件後結束。客戶端中途斷線時 SHALL 取消處理。

#### Scenario: 正常完成
- **WHEN** 以合法問題連線
- **THEN** 收到多個 `step` 事件，最後收到一個 `result` 事件後連線結束

#### Scenario: 客戶端斷線
- **WHEN** 收到第一個 `step` 事件後客戶端斷線
- **THEN** 後端取消處理，log 記錄取消

#### Scenario: 不合法輸入
- **WHEN** 問題為空白
- **THEN** 回傳 HTTP 422，不建立串流

### Requirement: 知識全文端點
系統 SHALL 提供依知識 ID 查詢全文的端點；ID 不存在時 SHALL 回傳 HTTP 404。

#### Scenario: 查詢定義
- **WHEN** 查詢「工作友善」的 ID
- **THEN** 回傳標題、類型與全文

#### Scenario: 不存在
- **WHEN** 查詢不存在的 ID
- **THEN** 回傳 HTTP 404
