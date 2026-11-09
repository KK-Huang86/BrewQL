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
3. 匯入後在頁面上方選擇資料來源（`…-prom`、`…-logs`）與環境（`local` 或 `demo`）。

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
