## 1. 後端

- [ ] 1.1 測試 + 實作：log 改為 JSON 格式，保留既有結構化欄位，不含憑證；驗證：測試由紅轉綠
- [ ] 1.2 測試 + 實作：`/metrics` 與各指標（結果、各階段耗時、token、Guardrail 原因、每日上限），標籤只有固定列舉值；驗證：測試由紅轉綠

## 2. 收集

- [ ] 2.1 docker compose 加入 Alloy（`observability` profile）、Alloy 設定（Docker log → Loki、`/metrics` → Mimir）、nginx access log 改 JSON；Grafana Cloud 設定同步 `.env.example`；驗證：未設定時 `docker compose up` 正常，設定後 Grafana Cloud 查得到 log 與指標
- [ ] 2.2 確認 `/metrics` 不對外；驗證：經 nginx 請求 `/metrics` 回 404

## 3. Dashboard 與告警

- [ ] 3.1 建立 dashboard 並匯出 JSON 到 `observability/`；驗證：從 JSON 匯入可重建
- [ ] 3.2 告警規則（5xx 比例、p95、Guardrail 失敗、每日上限）存到 `observability/`；驗證：讓 Guardrail 版本失效（fail closed），告警觸發

- [ ] 3.3 成本：模型與 Guardrail 單價設定、估算成本面板；Terraform 建立 Grafana 唯讀 IAM role（external ID），Grafana Cloud AWS 整合讀取 `AWS/Bedrock` 與 `AWS/Bedrock/Guardrails`；驗證：同一天的 token 數兩邊一致

## 4. 驗證

- [ ] 4.1 實際提問各種類型（正常、拒答、反問、攔截、限流），截圖 dashboard 放進 README；驗證：每個面板都有資料
