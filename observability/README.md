# Observability

BrewQL 的監控設定（OpenSpec change `observe-with-grafana`）。資料由 Grafana Alloy 推送到 Grafana Cloud，所有 log 與指標帶 `project="brewql"` 與 `env`（`local` 或 `demo`）。

```
observability/
├── alloy/config.alloy       # Alloy：backend /metrics、主機、容器、容器 log → Grafana Cloud
├── dashboards/brewql.json   # Dashboard
└── alerts/                  # 告警規則
```

## 啟動 Alloy

1. 在 `.env` 填入 `GRAFANA_CLOUD_*`（名稱見 `.env.example`）。token 只需要 `metrics:write` 與 `logs:write`。
2. `docker compose --profile observability up -d`
3. Alloy 的除錯介面：<http://127.0.0.1:12345>（只綁本機）。

不加 `--profile observability` 時 Alloy 不會啟動，其餘服務照常運作。

## 匯入 dashboard

1. Grafana Cloud → **Dashboards** → **New** → **Import**。
2. 上傳 `observability/dashboards/brewql.json`，資料夾選 `BrewQL`（沒有就先建立）。
3. 匯入後在頁面上方選擇資料來源（`…-prom`、`…-logs`、CloudWatch）與環境（`local` 或 `demo`）。

## 連接 CloudWatch（成本對帳）

Grafana Cloud 以 Assume Role 讀取 `AWS/Bedrock` 指標，不使用 access key。

1. **Connections** → **Data sources** → **Add new data source** → **CloudWatch**，Authentication Provider 選 **Grafana Assume Role**。頁面會顯示 Grafana 的 AWS 帳號 ID 與這個 stack 的 external ID。
2. 把兩個值寫進 `infra/terraform/terraform.tfvars`（已 git-ignore）的 `grafana_aws_account_id` 與 `grafana_external_id`，以 `brewql-deployer` 執行 `terraform apply`。建立的 `brewql-grafana-cloudwatch-read` 只能讀 CloudWatch 指標，trust policy 要求 external ID，其他 Grafana stack 無法使用。
3. 把輸出的 `grafana_cloudwatch_role_arn` 填入 Assume Role ARN，Default Region 選 `us-east-1`，**Save & test**。metrics 通過即可；logs 回 AccessDenied 是預期結果（role 沒有 `logs:*`）。

讀對帳面板時注意：

- 兩邊都來自 Bedrock 回應的 usage，原始數字相同。應用程式的數字由 Prometheus `increase()` 推算，會有小數與少量誤差；CloudWatch 約延遲數分鐘，並包含 eval 與 smoke 腳本的呼叫。
- backend 重啟後若在 Alloy 下一次抓取（15 秒）前就答題，且新的計數已超過重啟前的值，Prometheus 看不出計數器重置，該題 token 會少算。要精確比較時，用 Grafana Explore 查 CloudWatch `Sum`（period 300）與 backend `/metrics` 的原始計數。

## 畫面

| | |
|---|---|
| ![總覽與結果分布](../docs/images/grafana-overview.png) | ![耗時、成本與 Guardrail](../docs/images/grafana-latency-cost.png) |
| ![成本對帳](../docs/images/grafana-reconciliation.png) | ![主機與容器資源](../docs/images/grafana-resources.png) |
| ![Backend 警告與錯誤 log](../docs/images/grafana-logs.png) | |

在 UI 修改 dashboard 後，用 **Export** → **Export as JSON**（不勾 *Export for sharing externally*）覆蓋 repo 的檔案，再開 PR。

## 匯入告警規則

規則以 Prometheus rule 格式存在 `observability/alerts/`，匯入成 Grafana-managed alert rules：

1. **Alerting** → **Contact points**：建立通知管道（例如 email）。聯絡資訊只放在 Grafana，不進 repo。
2. **Alerting** → **Notification policies**：預設 policy 指向該 contact point。
3. **Alerting** → **Alert rules** → **Import to Grafana-managed rules**：
   - 來源選 **Prometheus YAML file**，上傳 `brewql-prometheus.yml`，資料來源選 `…-prom`，資料夾選 `BrewQL`。
   - 再匯入一次 `brewql-loki.yml`，資料來源選 `…-logs`。
4. 規則以 `env` 分組告警：本機（`local`）與部署（`demo`）各自觸發。不想收本機告警時，在 notification policy 加一條 `env=local` 的 policy 指向不通知的 contact point，或建立 silence。

修改規則時改 repo 的 YAML（CI 以 `promtool check rules` 檢查 Prometheus 規則），再重新匯入。
