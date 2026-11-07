## Context

`refuse-and-clarify` 之後，每次提問已經有 Guardrail 結果、耗時與 token 的 log 欄位，但只輸出成文字到容器的標準輸出。Demo 是單一主機、單人維運。

## Goals / Non-Goals

**Goals:** 一眼看出延遲、拒答率、成本與故障；設定可重建；沒有 Grafana 憑證時本機開發不受影響。

**Non-Goals:** traces、長期保存、自架監控。

## Decisions

### D1. Grafana Alloy + Grafana Cloud
Alloy 是單一 collector，同時處理 log（Docker → Loki）與 metrics（抓取 `/metrics` → Mimir），compose 多一個容器即可。Grafana Cloud 免費方案省去自架 Prometheus、Loki、Grafana 的維運。
- 替代方案：CloudWatch → 綁定 AWS、dashboard 能力較弱，且本機開發無法使用。原本 `record-audit-log` 規劃的 CloudWatch 改由這裡取代，只保留一條 log 管線。

### D2. Alloy 放在 compose 的 `observability` profile
沒有設定 Grafana Cloud 憑證時不啟動，本機 `docker compose up` 照常運作；部署主機以 `--profile observability` 啟動。

### D3. 指標設計：低基數標籤
| 指標 | 類型 | 標籤 |
|---|---|---|
| `brewql_ask_total` | counter | `status`、`refusal_source`、`error_kind` |
| `brewql_stage_seconds` | histogram | `stage`（`input_guard`、`model`、`db`） |
| `brewql_llm_tokens_total` | counter | `direction`（`input`、`output`） |
| `brewql_guardrail_blocks_total` | counter | `reason` |
| `brewql_daily_limit_hits_total` | counter | （無） |

標籤值都是固定的列舉，MUST NOT 放問題原文、SQL 或 IP，避免基數爆炸與資料外洩。

### D4. 問題原文不進一般 log 與指標
應用程式 log 與 metrics 只有結果與數值。問題原文只出現在 `record-audit-log` 的稽核事件（`event=ask_audit`），由該 ticket 決定保存方式。

### D5. `/metrics` 不對外
`/metrics` 由 backend 提供，nginx 只轉發 `/api/`，backend port 只綁 127.0.0.1（本機）或不對外開放（部署），所以只有同一個 compose 網路裡的 Alloy 能抓取。

### D6. Dashboard 與告警以程式碼保存
匯出的 dashboard JSON 與告警規則存在 `observability/`，README 說明匯入步驟。比手動在 UI 點選更容易 review 與重建。

### D7. 成本：應用程式估算 + AWS 端對帳
兩個來源並列在同一個 dashboard：
- **應用程式估算（即時、可拆到每題）**：`brewql_llm_tokens_total` 依模型與方向計數；Guardrail 依文字單位（每 1,000 字元 1 單位）計數。乘上設定的單價（模型、Guardrail 各一組，存在設定檔），得到每題與每日的估算成本，和 `eval-golden-set` 用同一組單價。
- **AWS 端數字（事實來源）**：Grafana Cloud 的 AWS 整合讀取 CloudWatch 的 `AWS/Bedrock`（`Invocations`、`InputTokenCount`、`OutputTokenCount`，依 `ModelId`）與 `AWS/Bedrock/Guardrails`（呼叫與攔截次數）。兩邊的 token 數應該一致，不一致代表有呼叫沒有被記錄。
- **實際帳單**：以 AWS Budgets 與 Cost Explorer（服務別、`Project=brewql` 標籤）為準；`deploy-public-demo` 建立 Budgets。
- 讀取 CloudWatch 用 Terraform 建立的 IAM role（Grafana Cloud 以 external ID assume），只有 `cloudwatch:GetMetricData`、`cloudwatch:ListMetrics` 等唯讀權限，沒有 access key。這是第三個身分：執行期 `brewql`、部署期 `brewql-deployer`、監控唯讀 role。

## Risks / Trade-offs

- [Grafana Cloud token 外洩] → 只放 `.env`；token 只授予寫入 log 與 metrics 的權限
- [免費方案額度或保存期限調整] → 用量很低；超過時只影響監控，不影響服務
- [Alloy 故障] → 只影響監控資料，不影響回答使用者
