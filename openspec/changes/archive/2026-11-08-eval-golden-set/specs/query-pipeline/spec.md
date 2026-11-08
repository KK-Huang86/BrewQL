## ADDED Requirements

### Requirement: 回報用量與耗時
每次回答 SHALL 在流程結果中回報該問題所有模型呼叫的累計輸入 token、輸出 token、使用的模型 ID、輸入 Guardrail 依政策分開的計費 units（denied topic、content filter），以及整體耗時（毫秒）。這些用量 MUST NOT 出現在 `/api/ask` 回應。

#### Scenario: 經過修正的問題
- **WHEN** 一個問題經過 2 次模型呼叫才成功
- **THEN** 回報的 token 為兩次呼叫的總和

#### Scenario: 被輸入 Guardrail 擋下
- **WHEN** 問題被輸入 Guardrail 擋下
- **THEN** token 為 0，Guardrail units 為該次檢查的 topic 與 content units

### Requirement: 模型知道今天的日期
產生 SQL 時，系統 SHALL 在送給模型的 system prompt 中提供今天的日期（台北時間），並說明早於今天的期間是可以查詢的歷史資料，只有推估今天以後的數值才是預測未來。

#### Scenario: 查詢過去的年份
- **WHEN** 今天是 2026-11-08，使用者問「2025 年每月新上架幾家咖啡店」
- **THEN** 送出的 system prompt 含有 `2026-11-08`，問題被當成歷史資料查詢而不是預測未來

#### Scenario: 跨日
- **WHEN** 台北時間已經是隔天、UTC 仍是前一天
- **THEN** 提供的日期為台北時間的日期
