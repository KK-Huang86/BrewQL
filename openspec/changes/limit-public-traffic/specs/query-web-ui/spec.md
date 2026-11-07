## ADDED Requirements

### Requirement: 顯示限流原因
收到 HTTP 429 時，介面 SHALL 顯示回應中的 `message`（例如「請求太頻繁，請稍後再試」），送出按鈕 SHALL 恢復可用，讓使用者稍後重試。

#### Scenario: 被限流
- **WHEN** 提問回應為 HTTP 429
- **THEN** 顯示「請求太頻繁，請稍後再試」，不顯示表格
