## Purpose

讓 BrewQL 上線後的延遲、結果分布、成本與故障可以被觀察與告警，而且設定可以從 repo 重建。

## ADDED Requirements

### Requirement: JSON 格式 log
應用程式 log SHALL 以每行一個 JSON 物件輸出，至少包含時間、等級、logger 名稱、訊息，以及該事件的結構化欄位（例如 `latency_ms`、`input_tokens`、`reasons`）。log MUST NOT 包含 AWS 憑證、Grafana token 或資料庫密碼。

#### Scenario: Guardrail 檢查
- **WHEN** 一個問題經過輸入檢查
- **THEN** 標準輸出有一行可被 JSON 解析的 log，含 `blocked`、`reasons`、`latency_ms`

### Requirement: Prometheus 指標
後端 SHALL 提供 `GET /metrics`（Prometheus 格式），包含提問結果計數（依 `status`、`refusal_source`、`error_kind`）、各階段耗時（`input_guard`、`model`、`db`）、token 用量與 Guardrail 攔截原因。指標標籤 MUST 只使用固定列舉值，MUST NOT 包含問題原文、SQL 或使用者 IP。`/metrics` MUST NOT 經由 nginx 對外公開。

#### Scenario: 被輸入防護拒答
- **WHEN** 一個問題被 Guardrail 以 prompt attack 攔下
- **THEN** `brewql_ask_total{status="refused",refusal_source="input_guardrail"}` 加 1，`brewql_guardrail_blocks_total{reason="prompt_attack"}` 加 1，`model` 階段沒有新的觀測值

#### Scenario: 對外不可存取
- **WHEN** 從公開網址請求 `/metrics`
- **THEN** 回傳 404，不含任何指標

### Requirement: 收集與推送
系統 SHALL 以 Grafana Alloy 收集容器 log 與 `/metrics`，推送到設定的 Grafana Cloud。未設定 Grafana Cloud 憑證時，其餘服務 MUST 照常啟動與運作。Alloy 或 Grafana Cloud 故障 MUST NOT 影響回答使用者。

#### Scenario: 本機沒有設定
- **WHEN** 未設定 Grafana Cloud 憑證時執行 `docker compose up`
- **THEN** Alloy 不啟動，提問正常

#### Scenario: Grafana Cloud 無法連線
- **WHEN** Alloy 推送失敗
- **THEN** 提問仍然正常回答

### Requirement: Dashboard 與告警以程式碼保存
Dashboard 與告警規則 SHALL 存在 repo 中，至少涵蓋：結果分布與拒答來源、各階段 p50／p95 耗時、每日 token 與估算成本、Guardrail 攔截原因、nginx 429 次數。告警 SHALL 至少包含：5 分鐘內 5xx 比例超過門檻、p95 總耗時超過門檻、Guardrail 呼叫失敗、每日提問上限被觸發。

#### Scenario: Bedrock 故障
- **WHEN** 5 分鐘內大部分提問回 502
- **THEN** 觸發 5xx 告警

### Requirement: 成本可見與對帳
Dashboard SHALL 顯示依模型的 token 用量、Guardrail 文字單位用量，以及依設定單價計算的每題與每日估算成本。Dashboard SHALL 同時顯示 AWS CloudWatch 的 Bedrock 呼叫次數與 token 數，供與應用程式數字對帳。讀取 CloudWatch MUST 使用只有唯讀權限的 IAM role（由 Terraform 建立、以 external ID 限制），MUST NOT 使用 access key。

#### Scenario: 對帳
- **WHEN** 一天內實際提問 20 題
- **THEN** dashboard 上應用程式記錄的 token 總數與 CloudWatch `AWS/Bedrock` 的 token 數一致，並顯示當日估算成本

#### Scenario: 監控角色權限
- **WHEN** 檢查 Grafana 使用的 IAM role
- **THEN** 只有 CloudWatch 讀取權限，沒有 Bedrock 呼叫或任何寫入權限
