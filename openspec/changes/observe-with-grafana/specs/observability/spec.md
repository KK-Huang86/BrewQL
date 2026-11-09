## Purpose

讓 BrewQL 上線後的延遲、結果分布、成本與故障可以被觀察與告警，而且設定可以從 repo 重建。

## ADDED Requirements

### Requirement: JSON 格式 log
應用程式 log SHALL 以每行一個 JSON 物件輸出，至少包含 `time`、`level`、`logger`、`message`，以及該事件的結構化欄位（例如 `latency_ms`、`input_tokens`、`reasons`）。log MUST NOT 包含問題原文、AWS 憑證、Grafana token 或資料庫密碼。無法序列化的欄位值 SHALL 轉成字串，不得讓記錄 log 失敗。nginx 的 access log SHALL 同樣以 JSON 輸出，包含來源 IP、method、不含 query string 的路徑、狀態碼與耗時，MUST NOT 包含 request body。

#### Scenario: Guardrail 檢查
- **WHEN** 一個問題經過輸入檢查
- **THEN** 標準輸出有一行可被 JSON 解析的 log，含 `blocked`、`reasons`、`latency_ms`，且不含問題原文

#### Scenario: nginx 限流
- **WHEN** 一個請求被 nginx 以 429 擋下
- **THEN** nginx access log 有一行可被 JSON 解析的紀錄，`status` 為 429，`uri` 不含 query string

### Requirement: Prometheus 指標
後端 SHALL 提供 `GET /metrics`（Prometheus 格式），由 `/api/ask` 記錄：提問結果計數（依 `status`、`refusal_source`、`error_kind`）、總耗時與各階段耗時（`input_guard`、`model`、`db`）、依模型的 token 用量、Guardrail 攔截原因與文字單位、估算成本、每日上限的使用量、上限值與觸發次數。指標標籤 MUST 只使用固定列舉值與設定的模型 ID，MUST NOT 包含問題原文、SQL 或使用者 IP。eval 與 smoke 腳本 MUST NOT 產生指標。`/metrics` MUST NOT 經由 nginx 對外公開。

#### Scenario: 正常回答
- **WHEN** 一個問題成功回答
- **THEN** `brewql_ask_total{status="ok"}` 加 1，`input_guard`、`model`、`db` 三個階段各有一筆新的觀測值，`brewql_llm_tokens_total` 依模型與方向增加該題的 token 數

#### Scenario: 被輸入防護拒答
- **WHEN** 一個問題被 Guardrail 以 prompt attack 攔下
- **THEN** `brewql_ask_total{status="refused",refusal_source="input_guardrail"}` 加 1，`brewql_guardrail_blocks_total{reason="prompt_attack"}` 加 1，`model` 階段沒有新的觀測值

#### Scenario: 服務無法使用
- **WHEN** Bedrock 無法連線，`/api/ask` 回 502
- **THEN** `brewql_ask_total{status="error",error_kind="unavailable_model"}` 加 1

#### Scenario: 每日上限
- **WHEN** 當天額度用完後又有一個問題
- **THEN** `brewql_daily_limit_hits_total` 加 1，`brewql_daily_questions_used` 等於 `brewql_daily_question_limit`，`brewql_ask_total` 不變

#### Scenario: 模型不在單價表
- **WHEN** 回答問題的模型 ID 不在單價表
- **THEN** `brewql_unpriced_questions_total` 加 1，`brewql_estimated_cost_usd_total{component="model"}` 不增加

#### Scenario: 對外不可存取
- **WHEN** 從公開網址請求 `/metrics`
- **THEN** 回傳 404，不含任何指標

### Requirement: 收集與推送
系統 SHALL 以 Grafana Alloy 收集 backend 與 nginx 容器的 log 與 backend 的 `/metrics`，推送到設定的 Grafana Cloud。Alloy SHALL 只在 compose 的 `observability` profile 啟動。未啟用該 profile 或未設定 Grafana Cloud 憑證時，其餘服務 MUST 照常啟動與運作。Alloy 或 Grafana Cloud 故障 MUST NOT 影響回答使用者。Grafana Cloud token MUST 只放在 `.env`，不得寫進 repo 的設定檔。

#### Scenario: 本機沒有設定
- **WHEN** 未加 `--profile observability` 執行 `docker compose up`
- **THEN** Alloy 不啟動，提問正常

#### Scenario: Grafana Cloud 無法連線
- **WHEN** Alloy 推送失敗
- **THEN** 提問仍然正常回答

### Requirement: Dashboard 與告警以程式碼保存
Dashboard 與告警規則 SHALL 存在 repo 的 `observability/` 中，至少涵蓋：結果分布與拒答來源、各階段 p50／p95 耗時、每日 token 與估算成本（含「成本不完整」）、Guardrail 攔截原因、每日上限使用量、nginx 429 與 404 次數。告警 SHALL 至少包含：5 分鐘內 5xx 比例超過門檻、p95 總耗時超過門檻、Guardrail 無法使用、每日提問上限被觸發、nginx 429 次數暴增。通知管道的聯絡資訊 MUST NOT 存進 repo。

#### Scenario: Guardrail 無法使用
- **WHEN** Guardrail 版本設定錯誤，提問一律回 502
- **THEN** 觸發 Guardrail 無法使用的告警

#### Scenario: 從 repo 重建
- **WHEN** 把 `observability/` 的 dashboard JSON 匯入一個新的 Grafana Cloud stack
- **THEN** 每個面板都能顯示資料

### Requirement: 成本可見與對帳
Dashboard SHALL 顯示依模型的 token 用量、Guardrail 文字單位用量，以及依 `app/pricing.py` 單價計算的每日估算成本。Dashboard 或對帳腳本 SHALL 同時取得 AWS CloudWatch `AWS/Bedrock` 的呼叫次數與 token 數，供與應用程式數字對帳。讀取 CloudWatch MUST 使用只有 CloudWatch 唯讀權限的 IAM role（由 Terraform 建立），MUST NOT 使用 access key。

#### Scenario: 對帳
- **WHEN** 一段時間內只有 BrewQL 的 `/api/ask` 呼叫 Bedrock
- **THEN** 應用程式記錄的 token 總數與 CloudWatch `AWS/Bedrock` 同一段時間的 token 數一致

#### Scenario: 監控角色權限
- **WHEN** 檢查讀取 CloudWatch 的 IAM role
- **THEN** 只有 CloudWatch 讀取權限，沒有 Bedrock 呼叫或任何寫入權限
