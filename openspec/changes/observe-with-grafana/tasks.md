## 1. 後端

- [x] 1.1 JSON log（D6）：`app` logger 每行一個 JSON，含 `time`、`level`、`logger`、`message` 與 `extra` 欄位，無法序列化的值轉字串，例外帶 traceback；uvicorn access log 關閉；驗證：紅燈再綠燈
- [x] 1.2 各階段耗時（D4）：`AskUsage` 記錄 `input_guard`、`model`、`db` 每次呼叫的耗時（重試各一筆、被 Guardrail 擋下時沒有 `model`），pipeline 不 import 指標套件；驗證：紅燈再綠燈
- [x] 1.3 `/metrics` 與提問指標（D3）：`brewql_ask_total`（含 5xx 的 `unavailable_*`）、`brewql_ask_seconds`、`brewql_stage_seconds`、`brewql_llm_tokens_total`、`brewql_guardrail_blocks_total`、`brewql_guardrail_units_total`；每個測試獨立 registry；驗證：紅燈再綠燈
- [x] 1.4 成本與每日上限指標（D3、D5）：`brewql_estimated_cost_usd_total` 用 `pricing.cost_usd`、不在單價表時只加 `brewql_unpriced_questions_total`；`brewql_daily_questions_used`、`brewql_daily_question_limit`、`brewql_daily_limit_hits_total`；驗證：紅燈再綠燈

## 2. 收集

- [x] 2.1 nginx JSON access log（D7）：容器測試確認每行可被 JSON 解析、429 有紀錄、`uri` 不含 query string；驗證：紅燈再綠燈
- [x] 2.2 Alloy（D1、D2、D8、D8a、D11）：所有 log 與指標帶 `project="brewql"`；`observability/alloy/config.alloy`、compose `observability` profile、Grafana Cloud 變數同步 `.env.example`（只列名稱）；CI 以 `alloy fmt` 檢查設定；驗證：不加 profile 時 `docker compose up` 與提問正常；使用者設定 `.env` 後加 profile，Grafana Cloud 查得到 backend 與 nginx 的 log 與 `brewql_*` 指標
  - 結果（2026-11-09）：不加 profile 時 `docker compose config --services` 只有 db、backend、frontend；加 profile 後 Alloy 推送 metrics 1,560 筆、失敗 0，logs 34 筆、Loki 回 204；使用者在 Grafana Cloud Explore 查到 `{project="brewql"}` 的 nginx JSON log 與 `brewql_ask_seconds_bucket{project="brewql",service="backend"}`
- [x] 2.3 主機與容器資源（D8b）：Alloy 加 `prometheus.exporter.unix` 與 `prometheus.exporter.cadvisor`，唯讀掛載，relabel 只保留用到的指標；驗證：Grafana Cloud 查得到主機記憶體與檔案系統、`db`／`backend`／`frontend` 的 CPU 與記憶體，BrewQL 的 active series 少於 1,000
  - 結果（2026-11-09，本機 Docker Desktop）：Grafana Cloud 查到 `node_memory_MemAvailable_bytes{project="brewql",service="host",instance="brewql-alloy"}` 一條，以及 `db`、`backend`、`frontend`、`alloy` 的 `container_memory_working_set_bytes`；估算 BrewQL series：容器 12、主機約 180、backend 約 20 起，低於 1,000。容器網路流量在 Docker Desktop 上沒有資料，部署到 EC2 時再確認
- [x] 2.4 Alloy 故障不影響服務（D2）：Grafana Cloud URL 設成無法連線時提問照常；驗證：記錄結果
  - 結果（2026-11-09）：Alloy 的 Prometheus 與 Loki URL 改成 `unreachable.invalid` 後，Alloy log 出現 `Failed to send batch, retrying`、重試 84 筆、送出 0 筆；同時經 nginx 提問「台北市有幾家咖啡店？」回 `ok [[160]]`，約 3 秒，與平常相同。改回正確設定後恢復推送

## 3. Dashboard 與告警

- [ ] 3.1 Dashboard（D10）：結果分布、拒答來源、各階段 p50／p95、每日 token 與估算成本、成本不完整、Guardrail 原因、每日上限使用量、nginx 429／404、主機與容器資源，匯出 JSON 到 `observability/dashboards/`；驗證：從 JSON 匯入可重建
- [ ] 3.2 告警（D10）：八條規則匯出 YAML 到 `observability/alerts/`；驗證：本機把 Guardrail 版本設錯，Guardrail 無法使用的告警觸發；連續提問觸發 nginx 429 告警；停掉 `backend` 容器觸發容器停止告警

## 4. 成本對帳

- [ ] 4.1 查證 Grafana Cloud 免費方案能否以 assume role（external ID）連 CloudWatch（D5）；驗證：記錄結論與來源，決定走 data source 或本機對帳腳本
- [ ] 4.2 Terraform 唯讀 IAM role（只有 CloudWatch 讀取權限），依 4.1 的結論接上 Grafana Cloud 或對帳腳本；驗證：`terraform plan` 只新增該 role 與 policy；使用者 apply 後，一段時間內的 token 數兩邊一致

## 5. 驗證

- [ ] 5.1 實際提問各種類型（正常、拒答、反問、攔截、5xx、每日上限、nginx 限流），截圖 dashboard 放進 README；驗證：每個面板都有資料
