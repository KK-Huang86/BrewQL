## ADDED Requirements

### Requirement: 回報用量與耗時
每次回答 SHALL 在流程結果中回報該問題所有模型呼叫的累計輸入 token、輸出 token、使用的模型 ID、輸入 Guardrail 的計費 units，以及整體耗時（毫秒）。這些用量 MUST NOT 出現在 `/api/ask` 回應。

#### Scenario: 經過修正的問題
- **WHEN** 一個問題經過 2 次模型呼叫才成功
- **THEN** 回報的 token 為兩次呼叫的總和

#### Scenario: 被輸入 Guardrail 擋下
- **WHEN** 問題被輸入 Guardrail 擋下
- **THEN** token 為 0，Guardrail units 為該次檢查的計費 units
