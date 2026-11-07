## ADDED Requirements

### Requirement: 顯示修正次數
回應的 `attempts` 大於 1 時，介面 SHALL 顯示「經過 N 次修正」（N = attempts − 1）。

#### Scenario: 經過修正
- **WHEN** 回應 `status=ok`、`attempts=3`
- **THEN** 顯示「經過 2 次修正」

#### Scenario: 一次成功
- **WHEN** 回應 `attempts=1`
- **THEN** 不顯示修正次數
