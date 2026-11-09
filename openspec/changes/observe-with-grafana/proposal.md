## Why

評估（`eval-golden-set`）用固定題目在上線前量正確率；上線後還需要知道真實流量的狀況：慢在哪一關、多少問題被擋、被誰擋、每天花多少錢、Bedrock 或 Guardrail 是否故障、有沒有人在打限流。現在這些資訊只散落在容器的文字 log 裡，看不到趨勢也沒有告警。`limit-public-traffic` 加了每 IP 限流與每日上限，但觸發時只有 log，指標留到這裡。加入輕量的可觀測性，讓 BrewQL 從「能用」變成「能營運」。

## What Changes

- 應用程式 log 改為每行一個 JSON 物件（沿用既有的結構化欄位：耗時、token、Guardrail 原因）；uvicorn 的 access log 關閉，對外請求以 nginx 的 JSON access log 為準
- pipeline 記錄各階段耗時（`input_guard`、`model`、`db`）到既有的 `AskUsage`；pipeline 本身不碰指標
- 後端新增 Prometheus 格式的 `/metrics`，只由 `/api/ask` 的 handler 記錄：結果分布、各階段與總耗時、依模型的 token、Guardrail 攔截原因與文字單位、以 `app/pricing.py` 計算的估算成本、每日上限的使用量與觸發次數
- docker compose 新增 **Grafana Alloy**（`observability` profile）：收集容器 log 與 `/metrics`，推送到 **Grafana Cloud**（Loki + Prometheus，免費方案）
- Dashboard 與告警規則以 JSON／YAML 存在 `observability/`，可重建
- 成本對帳：Grafana Cloud 讀取 CloudWatch 的 `AWS/Bedrock` 指標，與應用程式記錄的 token 數並列（唯讀 IAM role，以 external ID 限制，無 access key）
- 告警：5xx 比例、p95 總耗時、Guardrail 呼叫失敗、每日提問上限觸發、nginx 限流次數暴增

### Non-goals

- Traces（OpenTelemetry → Tempo）：log 與 metrics 足以回答目前的問題，需要時再加
- 自架 Grafana／Prometheus／Loki：Demo 規模不值得維運成本
- 問題原文：只屬於 `record-audit-log`，不進一般 log 與指標
- 網域與 HTTPS：Grafana Cloud 由 Alloy 主動推送，不需要對外網址；HTTPS 屬於 `deploy-public-demo`

## Capabilities

### New Capabilities

- `observability`: JSON log、Prometheus 指標、log 與指標收集、dashboard、告警與成本對帳。

### Modified Capabilities

（無）

## Impact

- 新增：`backend/app/metrics.py`、`/metrics` 路由、`observability/`（Alloy 設定、dashboard、告警規則）
- 修改：`backend/app/logging_setup.py`（JSON）、`backend/app/pipeline.py`（各階段耗時）、`backend/app/main.py`（記錄指標）、`frontend/nginx/default.conf.template`（JSON access log）、`docker-compose.yml`（Alloy 服務與 profile）、`infra/terraform/`（Grafana 唯讀 IAM role）、CI（Alloy 設定格式檢查）
- 新依賴：`prometheus-client`
- 新設定：Grafana Cloud 的端點、帳號 ID 與 token（`.env`，同步 `.env.example`）
- 成本：Grafana Cloud 免費方案（log 與 metrics 約保留 14 天）；CloudWatch `GetMetricData` 依查詢量計費，dashboard 低頻刷新時每月低於 $1
- 依賴 ticket：`limit-public-traffic`（`/metrics` 不對外、每日上限、nginx 模板）；在 `record-audit-log` 與 `deploy-public-demo` 之前，部署時直接帶上
