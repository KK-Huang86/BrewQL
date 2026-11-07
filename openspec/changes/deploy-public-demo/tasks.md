## 1. Terraform

- [ ] 1.1 在既有 Terraform 加入 variables（管理者 IP、預算、email、instance type）與 outputs（公開 IP）；驗證：`terraform validate` 成功
- [ ] 1.2 IAM role、Bedrock policy、instance profile；驗證：`terraform plan` 中 policy 只含 Bedrock 動作
- [ ] 1.3 Security Group；驗證：`terraform plan` 只有 22（管理者 IP）與 80
- [ ] 1.4 EC2（SSM 取 AMI、IMDSv2、user data 安裝 docker 與 compose）；驗證：`terraform plan` 成功
- [ ] 1.5 AWS Budgets；驗證：`terraform plan` 成功

## 2. CI 與文件

- [ ] 2.1 README 加入部署、重新部署、銷毀步驟與成本說明；驗證：照步驟可從零部署

## 3. 實際部署

- [ ] 3.1 `terraform apply`、部署（`docker compose --profile observability up -d --build`）、透過公開 IP 提問；驗證：成功回答，主機上無 AWS access key，Budgets 已建立
- [ ] 3.2 上線檢查：從外部連續提問觸發 429、`/metrics` 回 404、Grafana Cloud 看得到請求；驗證：記錄結果
- [ ] 3.3 `terraform destroy`；驗證：資源已刪除（面試前再重新 apply）
