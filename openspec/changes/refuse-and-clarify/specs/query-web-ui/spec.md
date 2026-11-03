## ADDED Requirements

### Requirement: 顯示拒答與反問
`status=refused` 與 `status=clarify` 時，介面 SHALL 顯示 `message`，兩者與錯誤的樣式 MUST 可區分，且不顯示表格。拒答時 SHALL 標示來源（輸入防護或模型）。反問時 SHALL 讓使用者能直接修改原問題再送出。

#### Scenario: 輸入防護拒答
- **WHEN** 回應為 `status=refused`、`refusal_source=input_guardrail`
- **THEN** 顯示拒答原因並標示「輸入防護」

#### Scenario: 反問
- **WHEN** 回應為 `status=clarify`
- **THEN** 顯示反問內容，輸入框保留原問題供修改
