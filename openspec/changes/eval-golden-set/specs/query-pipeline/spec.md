## ADDED Requirements

### Requirement: 回報用量與耗時
每次回答 SHALL 回報該問題所有模型呼叫的累計輸入 token、輸出 token、使用的模型 ID，以及整體耗時（毫秒）。

#### Scenario: 經過修正的問題
- **WHEN** 一個問題經過 2 次模型呼叫才成功
- **THEN** 回報的 token 為兩次呼叫的總和
