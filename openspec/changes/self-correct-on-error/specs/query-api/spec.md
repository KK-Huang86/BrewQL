## ADDED Requirements

### Requirement: 回應包含嘗試次數
`POST /api/ask` 的 200 回應 SHALL 包含整數 `attempts`；5xx 回應沒有完成的回答，`attempts` MUST 為 0（即使重試途中已呼叫過模型）。

#### Scenario: 一般回應
- **WHEN** 問題第一次就成功
- **THEN** 回應 `attempts=1`

#### Scenario: 服務錯誤
- **WHEN** 輸入 Guardrail 無法使用
- **THEN** 回傳 HTTP 502，`attempts=0`
