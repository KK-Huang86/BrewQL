## ADDED Requirements

### Requirement: 顯示防護拒絕原因
當 SQL 被防護拒絕時，介面 SHALL 顯示被拒絕的原因與被拒絕的 SQL，樣式 SHALL 與一般錯誤（網路、伺服器）可區分。

#### Scenario: 被擋下的 SQL
- **WHEN** 回應為 `status=error`，原因為不允許查詢的資料表
- **THEN** 畫面顯示原因與該 SQL，樣式標示為「安全防護」
