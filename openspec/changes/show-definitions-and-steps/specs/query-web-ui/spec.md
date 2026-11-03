## ADDED Requirements

### Requirement: 即時步驟
提問時介面 SHALL 使用串流端點，即時顯示每個步驟的狀態（進行中、完成、失敗與原因），重試時顯示嘗試編號；收到 `result` 後依原本方式顯示結果。串流連線失敗時 SHALL 顯示錯誤並恢復可送出狀態。

#### Scenario: 顯示步驟
- **WHEN** 送出問題
- **THEN** 依序看到「檢索知識」「產生 SQL」「驗證」「執行」的狀態變化

#### Scenario: 顯示重試
- **WHEN** 第一次驗證失敗
- **THEN** 看到失敗原因與「第 2 次嘗試」

### Requirement: 知識來源面板
結果區 SHALL 列出 `sources`（類型與標題），點選後顯示該知識全文。`sources` 為空時不顯示面板。

#### Scenario: 點開定義
- **WHEN** 點選「工作友善」
- **THEN** 顯示其完整定義
