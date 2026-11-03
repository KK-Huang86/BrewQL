## Why

不是每個問題都該產生 SQL。要求修改資料、與數據無關、要預測未來的問題應該拒答；「最近熱門的店」這種缺少時間範圍或指標的問題應該反問。直接猜一個 SQL 給出看似正確的答案，比不回答更危險。另外，prompt injection（「忽略之前的指示…」）應該在問題進入模型之前就被攔下，而不是只靠 SQL 防護在最後一關擋住。

## What Changes

- 結構化輸出擴充為三種結果：SQL、拒答、反問（由 JSON schema 保證格式）
- 新增回應狀態 `refused`、`clarify`，兩者都不執行任何 SQL
- 模型安全機制拒絕（refusal）時視為拒答
- 新增輸入防護：問題先經 **Amazon Bedrock Guardrails** 檢查 prompt attack 與與數據無關的話題，被攔下時直接拒答、不呼叫模型
- Guardrail 以 Terraform 建立，CI 加入 Terraform 檢查
- 畫面以不同樣式顯示拒答與反問，並標示拒答來源（輸入防護／模型）

## Capabilities

### New Capabilities

- `input-guardrails`: 問題進入模型前的輸入檢查（Bedrock Guardrails）。

### Modified Capabilities

- `query-pipeline`: 結構化輸出新增拒答與反問。
- `query-web-ui`: 新增拒答與反問的顯示。
- `project-ci`: 新增 Terraform 檢查。

## Impact

- 修改：結構化輸出 schema、system prompt、流程、API 回應狀態、前端訊息元件
- 新增：`infra/terraform/`（目前只有 Guardrail 資源）、Terraform CI workflow
- 新依賴：boto3（呼叫 ApplyGuardrail）
- 成本：Guardrails 依檢查的文字量計費，Demo 用量極低
- 依賴 ticket：`ask-first-question`
