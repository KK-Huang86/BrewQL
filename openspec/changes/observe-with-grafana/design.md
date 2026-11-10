## Context

- 每次提問已經有結構化 log 欄位（`input_guard.py` 的 `blocked`、`reasons`、`latency_ms`；`llm.py` 的 `input_tokens`、`output_tokens`），但 `logging_setup.py` 只輸出成文字，`extra` 欄位沒有出現在輸出裡。
- `pipeline.AskUsage` 已經累計 token、Guardrail 文字單位與總耗時；`app/pricing.py` 是 eval 與指標共用的單價表（`cost_usd(usage)`）。各階段耗時目前只有 Guardrail 有。
- `limit-public-traffic` 之後：nginx 只轉發 `/api/ask`，`/metrics` 經公開網址回 404；backend port 只綁 `127.0.0.1`；每日上限在 `app/daily_limit.py`，觸發時只有 WARNING log。
- Demo 是單一主機、單一 backend process、單人維運。

## Goals / Non-Goals

**Goals:** 一眼看出延遲、結果分布、成本、故障，以及主機與容器資源；被攻擊（限流大量觸發）時收到告警；設定可從 repo 重建；沒有 Grafana 憑證時本機開發完全不受影響。

**Non-Goals:** traces、長期保存、自架監控、問題原文（屬於 `record-audit-log`）。

## Decisions

### D1. Grafana Alloy + Grafana Cloud
Alloy 是單一 collector，同時處理 log（Docker → Loki）與 metrics（抓取 `backend:8000/metrics` → Grafana Cloud Prometheus），compose 多一個容器即可。Grafana Cloud 免費方案省去自架 Prometheus、Loki、Grafana 的維運。Alloy 主動往外推送，不需要對外網址或網域。
- 替代方案：CloudWatch Logs／Metrics → 綁定 AWS、dashboard 能力較弱、本機開發無法使用。

### D2. Alloy 放在 compose 的 `observability` profile
沒有加 `--profile observability` 時 Alloy 不啟動，本機 `docker compose up` 照常運作；部署主機與要測監控時才加。Alloy 掛掉或 Grafana Cloud 連不上只影響監控資料：backend 不依賴 Alloy（`depends_on` 方向只有 Alloy → backend）。

### D3. 指標：低基數、固定列舉標籤

| 指標 | 類型 | 標籤 |
|---|---|---|
| `brewql_ask_total` | counter | `status`、`refusal_source`、`error_kind`（沒有值時為空字串） |
| `brewql_ask_seconds` | histogram | （無）：一題從進入 handler 到回應的總耗時 |
| `brewql_stage_seconds` | histogram | `stage`（`input_guard`、`model`、`db`） |
| `brewql_llm_tokens_total` | counter | `model`、`direction`（`input`、`output`） |
| `brewql_guardrail_blocks_total` | counter | `reason` |
| `brewql_guardrail_units_total` | counter | `policy`（`topic`、`content`） |
| `brewql_estimated_cost_usd_total` | counter | `component`（`model`、`guardrail`） |
| `brewql_unpriced_questions_total` | counter | （無）：模型不在單價表或 Guardrail 沒回報用量，成本會偏低 |
| `brewql_daily_questions_used` | gauge | （無）：今天已用額度 |
| `brewql_daily_question_limit` | gauge | （無） |
| `brewql_daily_limit_hits_total` | counter | （無） |

- 標籤值只有固定列舉與設定的模型 ID，MUST NOT 放問題原文、SQL 或 IP，避免基數爆炸與資料外洩。`reason` 取自 Guardrail 的固定原因代碼。
- 5xx（Guardrail、Bedrock、資料庫無法使用）記為 `status="error"` 加上 `error_kind="unavailable_guardrail"`／`"unavailable_model"`／`"unavailable_db"`，與 pipeline 的 `generation`／`guardrail`／`query` 區分。被每日上限擋下的請求只記 `brewql_daily_limit_hits_total`，不進 `brewql_ask_total`。
- 一題重試多次時，`model` 與 `db` 階段每次呼叫各記一筆觀測值。
- Histogram bucket 固定：0.1、0.25、0.5、1、2.5、5、10、20、30 秒（逾時上限 nginx 60 秒）。

### D4. 在哪裡量、在哪裡記
- **pipeline 量**：`AskUsage` 新增各階段耗時清單（每次呼叫一筆），pipeline 只負責寫入，不 import 任何指標套件。eval 與 smoke 腳本也走 pipeline，但不會產生指標。
- **API handler 記**：`/api/ask` 在回應前把 `AskResult` 與 `AskUsage` 交給 `app/metrics.py` 記錄。指標只反映真實流量，eval 的測試題不會混進 dashboard。
- 成本用 `pricing.cost_usd` 同一組單價（D5），不在 dashboard 另外乘單價。

### D5. 成本：應用程式估算 + AWS 端對帳
- **應用程式估算（即時）**：每題依 `app/pricing.py` 算出模型與 Guardrail 成本，累加到 `brewql_estimated_cost_usd_total`。單價只改 `pricing.py`。
- 模型不在單價表（例如換了模型 ID 忘了加價格）或 Guardrail 沒回報用量時，不猜價格：該題只加 `brewql_unpriced_questions_total`，dashboard 顯示「成本不完整」。
- **AWS 端數字（事實來源）**：Grafana Cloud 的 CloudWatch data source 讀取 `AWS/Bedrock` 的 `Invocations`、`InputTokenCount`、`OutputTokenCount`（依 `ModelId`），與 `brewql_llm_tokens_total` 並列。兩邊 token 數應該一致；不一致代表有呼叫沒被記錄，或有 BrewQL 以外的呼叫（例如 eval）。
- 讀取 CloudWatch 用 Terraform 建立的 IAM role，trust policy 只信任 Grafana Cloud 的 AWS 帳號並要求 external ID，權限只有 `cloudwatch:GetMetricData`、`cloudwatch:ListMetrics`、`cloudwatch:GetMetricStatistics`。這是第三個身分：執行期 `brewql`、部署期 `brewql-deployer`、監控唯讀 role。沒有 access key。
- Grafana Cloud 免費方案是否支援以 assume role 連 CloudWatch，在實作 D5 前先查證（tasks 4.1）。不支援時改用本機對帳腳本：以 `AWS_PROFILE=brewql` 讀 CloudWatch 與 Grafana Cloud 的 token 總數比較，role 仍由 Terraform 建立但改信任 `brewql` 使用者。
- 實際帳單以 AWS Budgets 與 Cost Explorer 為準，由 `deploy-public-demo` 建立。

### D6. JSON log
- `app` logger 每行輸出一個 JSON 物件：`time`（ISO 8601）、`level`、`logger`、`message`，加上呼叫時 `extra` 帶入的欄位；例外時加 `exc_info` 的文字。
- 欄位名稱不可覆蓋保留鍵；值無法序列化時轉成字串，不讓 log 本身拋錯。
- 問題原文不進 log（沿用 `_log_failure` 與 Guardrail log 的既有規則）。SQL 只出現在失敗重試的 WARNING log（既有行為），不進指標。
- uvicorn 的 access log 關閉：它只看得到 nginx 容器的 IP，對外請求以 nginx access log 為準。uvicorn 的錯誤 log 維持原格式。

### D7. nginx JSON access log
nginx 以 `log_format ... escape=json` 輸出一行一個 JSON：時間、`remote_addr`、method、`uri`（不含 query string）、`status`、`request_time`、`upstream_status`、`body_bytes_sent`。不記 request body 與 header。Loki 以 LogQL 從這些 log 計算 429 與 404 次數。
- IP 會保存在 Grafana Cloud Loki（約 14 天）。這是辨識攻擊來源的必要資訊；不進指標標籤。

### D8. Alloy 收集 Docker log
`discovery.docker` + `loki.source.docker` 讀取 Docker socket（唯讀掛載），只收有 `brewql.logs=true` 標籤的容器（只有這個 compose 檔的 `backend`、`frontend` 帶這個標籤），以 `service` 標籤區分。不另外以 compose 專案名稱過濾：專案名稱隨目錄名稱改變，標籤只出現在 repo 的 compose 檔，同一台主機只會有一份 BrewQL。JSON log 在 Alloy 端解析，`level` 轉成 Loki 標籤，其他欄位留在 log 內容中（避免高基數標籤）。
- 風險：Docker socket 即使唯讀掛載，仍能讀取所有容器的設定與環境變數。只給 Alloy、image 固定版本；Alloy 的除錯介面 port 12345 只綁 `127.0.0.1`，不對外。替代方案是掛載 `/var/lib/docker/containers`，但會失去容器名稱、只剩 ID。

### D8a. 共用 Grafana Cloud stack：以 `project` 標籤區分
Grafana Cloud 免費方案一個帳號只有一個 stack，BrewQL 會和其他專案共用同一組 Loki、Prometheus 與額度。Alloy 對所有 log 與指標加上 external label `project="brewql"` 與 `env`（`BREWQL_ENV`，本機預設 `local`、部署為 `demo`），dashboard 與告警的查詢一律帶 `project="brewql"`，放在 `BrewQL` 資料夾。BrewQL 使用獨立的 access policy token，不沿用其他專案的 token，停用時可以單獨撤銷。

### D8b. 主機與容器資源：Alloy 內建 exporter
- **主機**：`prometheus.exporter.unix`（node exporter），只開 `cpu`、`meminfo`、`loadavg`、`filesystem`、`diskstats`、`netdev`，掛載 `/proc`、`/sys`、`/` 為唯讀。
- **容器**：`prometheus.exporter.cadvisor`，讀 Docker socket、containerd socket 與 `/sys`、`/var/lib/docker` 唯讀，只保留有 `brewql.metrics=true` 標籤的容器（`db`、`backend`、`frontend`、`alloy`），以 `service` 標籤區分。
  - Docker 29 預設的 containerd image store（`overlayfs` driver）下，cAdvisor 要透過 containerd 找容器的檔案層：Alloy v1.10 的 cAdvisor 認不得這種儲存方式，所以 Alloy 固定為 v1.14.0 並掛載 `/run/containerd/containerd.sock`（實測 v1.10、v1.13 都抓不到容器）。
  - 網路卡只收 `eth|ens|enp|eno` 開頭的實體網卡；veth、bridge 與 tunnel 裝置只會增加 series。
- 額度：免費方案的 active series 有上限，與其他專案共用（D8a）。以 relabel 只保留 dashboard 與告警用到的指標（主機 CPU、記憶體、負載、檔案系統、磁碟 I/O、網路；容器 CPU、working set 記憶體），丟掉其餘；BrewQL 全部 series 目標在 1,000 以內。
- 本機 Docker Desktop 上的「主機」是 Docker 的 Linux VM，不是 Mac 本身；主機數字要到部署的 EC2 才有意義，本機只驗證管線能通。
- 不收容器網路：cAdvisor 要讀每個容器 process 的 `/proc/<pid>/net/dev`，Alloy 必須開 `pid: host` 才看得到，權限擴大到主機上所有 process；對外流量由主機網路與 nginx access log 看即可。
- 不在 backend 加 Python process 指標：容器層已經看得到 backend 的 CPU 與記憶體。

### D9. `/metrics` 不對外
`/metrics` 由 backend 提供，沒有驗證。只能從 compose 網路內存取：nginx 白名單不轉發 `/metrics`（`limit-public-traffic` D6，已有容器測試），backend port 只綁 `127.0.0.1`，部署主機的 security group 不開 8000。

### D10. Dashboard 與告警以程式碼保存
- Dashboard：在 Grafana Cloud UI 建好後匯出 JSON 存在 `observability/dashboards/`，README 說明匯入步驟。
- 告警：Grafana-managed alert rules 匯出成 YAML 存在 `observability/alerts/`。通知管道（contact point，含 email）在 UI 設定，不進 repo。
- 告警門檻（初始值，之後依實際流量調整）：
  - 5 分鐘內 5xx 比例 > 20% 且至少 5 題
  - 10 分鐘內 p95 總耗時 > 10 秒
  - 5 分鐘內出現 Guardrail 無法使用（`error_kind="unavailable_guardrail"`）
  - 每日上限被觸發（`brewql_daily_limit_hits_total` 增加）
  - 5 分鐘內 nginx 429 超過 50 次（攻擊訊號）
  - 主機檔案系統使用率 > 85%
  - 主機記憶體使用率 > 90% 持續 10 分鐘
  - `backend` 5 分鐘內抓不到 `/metrics`（`up == 0`）：容器停了、卡住或 `/metrics` 壞掉都會觸發。原本設計用 cAdvisor 的 CPU／記憶體資料消失判斷，但 cAdvisor 的 series 在容器停止後會保留一段時間（`storage_duration`），`up` 更直接，也涵蓋容器還在但服務沒回應的情況

### D11. 設定
`.env`（同步 `.env.example`，不提供真實值）：
- `GRAFANA_CLOUD_PROMETHEUS_URL`、`GRAFANA_CLOUD_PROMETHEUS_USER`
- `GRAFANA_CLOUD_LOKI_URL`、`GRAFANA_CLOUD_LOKI_USER`
- `GRAFANA_CLOUD_TOKEN`：access policy token，只授予 `metrics:write`、`logs:write`
Alloy 設定檔以 `sys.env(...)` 讀取，token 不寫進設定檔。

### D12. 測試
- 後端單元測試：JSON formatter 的輸出；pipeline 各階段耗時；以 `TestClient` 打 `/api/ask` 後讀 `/metrics` 文字，檢查計數與標籤（每個測試用獨立的 `CollectorRegistry`，避免測試間互相影響）。
- nginx：沿用 `frontend/nginx-tests`，加一個測試確認 access log 是可解析的 JSON 且不含 query string。
- Alloy：CI 以固定版本的 Alloy image 執行 `alloy fmt -t` 與 `alloy validate` 檢查設定語法與元件設定；告警規則以 `promtool check rules` 檢查（同一個 workflow），避免匯入 Grafana 時才發現規則寫錯。實際推送到 Grafana Cloud 是手動驗證（需要使用者的帳號），不進 CI。

## Risks / Trade-offs

- [Grafana Cloud token 外洩] → 只放 `.env`；token 只能寫入 log 與 metrics，不能讀取或管理
- [Docker socket 權限] → 見 D8；只給 Alloy
- [免費方案額度或保存期限調整] → 用量很低；超過時只影響監控，不影響服務
- [Alloy 或 Grafana Cloud 故障] → 只影響監控資料，不影響回答使用者（D2）
- [單價表過時] → 對帳面板顯示 token 是否一致；金額以 Cost Explorer 為準
- [計數在記憶體] → backend 重啟後 counter 歸零，Prometheus 的 `rate`／`increase` 會處理 counter reset；每日上限 gauge 重啟後同樣歸零（與 `daily_limit` 行為一致）
