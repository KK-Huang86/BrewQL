## ADDED Requirements

### Requirement: 供給缺口故事
內湖區的搜尋量 MUST 排在所有行政區前 3 名，且其搜尋落空率（`result_count = 0` 的搜尋數 ÷ 該區搜尋數）MUST 是所有行政區中最高。調整行政區分布 MUST NOT 破壞既有故事（考試季效應、註冊後才搜尋、日期範圍），也 MUST NOT 改變 `cafes`。

#### Scenario: 落空率排名
- **WHEN** 依行政區計算搜尋落空率並由高到低排序
- **THEN** 第一名是內湖區

#### Scenario: 搜尋量排名
- **WHEN** 依行政區計算搜尋量並由高到低排序
- **THEN** 內湖區在前 3 名
