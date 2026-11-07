## Why

面試需要一個能公開操作的網址，而且要「面試前一鍵建立、面試後一鍵銷毀」以控制成本。路徑打通後就可以部署，之後每完成一個 ticket 都能重新部署，讓線上版本隨時可 Demo。以 Terraform 管理也能展示 IaC 與雲端安全的做法。

## What Changes

- 在既有的 `infra/terraform/`（已有 Guardrail）加入：EC2（`t4g.small`）、IAM role 與 instance profile（只允許呼叫 Bedrock 模型）、Security Group、AWS Budgets
- 主機以 docker compose 執行全部服務，含 `observability` profile（Grafana Alloy）
- 上線前確認 `limit-public-traffic` 的限流與每日上限生效
- README：部署、重新部署、銷毀步驟與成本說明

## Capabilities

### New Capabilities

- `cloud-infrastructure`: Demo 部署所需的 AWS 資源、存取限制與成本控管。

### Modified Capabilities

（無；Terraform CI 已在 `refuse-and-clarify` 建立）

## Impact

- 修改：`infra/terraform/`；新增：README 部署章節
- 成本：EC2 約 US$12／月（只在 Demo 期間開機），Bedrock 依用量
- 依賴 ticket：`refuse-and-clarify`（已建立 Terraform 與 Guardrail）、`limit-public-traffic`（公開前必須有限流與每日上限）、`observe-with-grafana`（上線後的監控與告警）、`record-audit-log`（公開後陌生人的提問要可稽核）；建議在 ticket 6～8（圖表）之後，讓線上 Demo 有完整內容；之後每個 ticket 完成可重新部署
