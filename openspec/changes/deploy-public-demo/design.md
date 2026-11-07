## Context

單人專案、只在面試期間運作，總預算約 US$15～45。

## Goals / Non-Goals

**Goals:** 一鍵建立與銷毀、無長期憑證、成本可控、能重複部署新版本。

**Non-Goals:** HTTPS 與網域、高可用、自動部署（CD）、遠端 state。

## Decisions

### D1. EC2 + instance profile，而非 Lightsail
Lightsail 無法掛 IAM role，只能在主機放 access key；EC2 instance profile 提供自動輪替的臨時憑證。`t4g.small`（ARM）約 US$12／月，足夠執行 Postgres + backend + nginx。
- 替代方案：ECS Fargate + RDS → 更正式，但成本與複雜度遠超 Demo 需求。

### D2. 預設 VPC、SSM 參數取 AMI
減少資源數量；AMI 用 Amazon Linux 2023 ARM 的公開 SSM 參數，不寫死 ID。

### D3. 部署方式：SSH 進主機 `git pull` + `docker compose up -d --build`
不做 CD，步驟寫在 README。Demo 資料庫由 init 腳本自動建立；RAG 知識庫在部署後執行一次匯入。

### D4. State 放本機
單人使用，不建立 S3 backend；`.gitignore` 已排除 state。

### D6. 上線檢查
公開前 MUST 確認：限流與每日上限生效、`/metrics` 與管理端點不對外、Alloy 以 `--profile observability` 啟動並在 Grafana Cloud 看得到資料。Grafana Cloud token 放在主機的 `.env`（第三方憑證無法用 IAM role 取代），檔案權限只限部署使用者讀取。

### D5. Bedrock 權限
允許 `bedrock:InvokeModel` 與 `bedrock:InvokeModelWithResponseStream`，資源限定在 Anthropic Claude、Titan Embeddings 的模型與 inference profile。實際呼叫被拒時，依錯誤訊息補上缺少的動作並記錄。

## Risks / Trade-offs

- [忘記銷毀持續計費] → 預算警示；README 明列銷毀步驟
- [SDK 所用 endpoint 需要不同 IAM 動作] → 部署後實際提問驗證
- [公開網址被濫用而產生 Bedrock 費用] → nginx 依 IP 限流與全域每日提問上限（`limit-public-traffic`）；Grafana 告警；預算警示；只在面試期間開機
