## Purpose

以 Terraform 管理 Demo 部署所需的 AWS 資源，讓環境可以一鍵建立與銷毀，同時避免長期憑證外洩與費用失控。

## ADDED Requirements

### Requirement: 基礎設施即程式碼
所有 AWS 資源 SHALL 由 Terraform 建立與銷毀。Terraform state、變數檔與任何憑證 MUST NOT 進入版本控制。

#### Scenario: 敏感檔案不進版控
- **WHEN** 執行 `terraform apply` 後執行 `git status`
- **THEN** state 與變數檔不在待追蹤清單

#### Scenario: 一鍵銷毀
- **WHEN** 執行 `terraform destroy`
- **THEN** 主機、IAM role、Security Group 全部刪除

### Requirement: 無長期憑證呼叫 Bedrock
主機 MUST 透過 IAM role 取得臨時憑證，權限 MUST 只包含呼叫 Claude、Titan Embeddings 模型與套用指定 Guardrail 所需的動作，MUST NOT 建立 IAM user access key。主機 MUST 要求 IMDSv2。

#### Scenario: 主機權限
- **WHEN** 檢查主機 IAM role 的 policy
- **THEN** 只有 Bedrock 呼叫模型的權限

#### Scenario: 主機上可提問
- **WHEN** 部署完成後透過公開網址提問
- **THEN** 成功回答，主機上沒有 AWS access key 檔案

### Requirement: 網路存取限制
SSH MUST 只開放給設定的管理者 IP；HTTP（80）SHALL 對外開放；資料庫與 backend port MUST NOT 對外開放。

#### Scenario: Security Group
- **WHEN** 檢查 inbound 規則
- **THEN** 只有 22（管理者 IP）與 80

### Requirement: 成本控管
系統 SHALL 建立每月預算（預設 US$20，可設定），預測或實際花費超過 80% 時寄信到設定的 email。

#### Scenario: 預算警示
- **WHEN** 當月預測花費超過預算 80%
- **THEN** 設定的 email 收到通知
