## Why

評估（`eval-golden-set`）用固定題目在上線前量正確率；上線後還需要知道真實流量的狀況：慢在哪一關、多少問題被擋、被誰擋、每天花多少錢、Bedrock 或 Guardrail 是否故障。現在這些資訊只散落在容器 log 裡，看不到趨勢也沒有告警。加入輕量的可觀測性，讓 BrewQL 從「能用」變成「能營運」。

## What Changes

- 應用程式 log 改為 JSON 格式（沿用既有欄位：耗時、token、Guardrail 原因）
- 後端新增 Prometheus 格式的 `/metrics`：提問結果分布、各階段耗時、token 用量、Guardrail 攔截原因
- docker compose 新增 **Grafana Alloy**（`observability` profile）：收集容器 log 與 `/metrics`，推送到 **Grafana Cloud**（Loki + Mimir，免費方案）
- Dashboard 與告警規則以 JSON／YAML 存在 repo，可重建
- 成本：依模型的 token 與 Guardrail 用量、每題與每日估算成本；並以 Grafana Cloud 的 AWS 整合讀取 CloudWatch 的 Bedrock 指標對帳（唯讀 IAM role，無 access key）
- 告警：5xx 比例、p95 耗時、Guardrail 失敗、每日提問上限觸發、nginx 限流次數

### Non-goals

- Traces（OpenTelemetry → Tempo）：log 與 metrics 足以回答目前的問題，需要時再加
- 自架 Grafana／Prometheus：Demo 規模不值得維運成本

## Capabilities

### New Capabilities

- `observability`: 指標、log 收集、dashboard 與告警。

### Modified Capabilities

（無）

## Impact

- 新增：`backend/app/metrics.py`、`/metrics` 路由、`observability/`（Alloy 設定、dashboard、告警規則）
- 修改：`infra/terraform/`（Grafana 唯讀 IAM role）、log 格式（JSON）、docker compose（Alloy 服務與 profile）、nginx access log 格式（JSON，供統計 429）
- 新依賴：`prometheus-client`
- 新設定：Grafana Cloud 的端點與 token（`.env`，同步 `.env.example`）
- 成本：Grafana Cloud 免費方案（log 與 metrics 約保留 14 天）
- 依賴 ticket：`refuse-and-clarify`（結果與拒答來源標籤）；建議在 `eval-golden-set` 之後、`deploy-public-demo` 之前，部署時直接帶上
