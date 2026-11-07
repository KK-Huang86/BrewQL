## ADDED Requirements

### Requirement: Terraform 檢查
CI SHALL 在每個 PR 執行 `terraform fmt -check` 與 `terraform validate`（不需要 AWS 憑證），任一失敗 MUST 讓 CI 失敗。

#### Scenario: 格式不符
- **WHEN** PR 中的 Terraform 檔案未經格式化
- **THEN** CI 失敗
