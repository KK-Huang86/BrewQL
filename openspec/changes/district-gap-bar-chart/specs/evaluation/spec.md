## ADDED Requirements

### Requirement: 行政區比較題
黃金測試集 SHALL 加入至少 3 題行政區比較題，其中至少 1 題涉及搜尋落空率、1 題為困難題（例如「搜尋量前 5 名的行政區中，落空率最高的是哪一區？」）。

#### Scenario: 題目可執行
- **WHEN** 以試跑模式執行評估
- **THEN** 新增題目的參考 SQL 都可執行
