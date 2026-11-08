# project-ci Specification

## Purpose
以自動化檢查守住程式碼品質與「程式碼和 spec 同步」的專案規則：每個 PR 都必須通過後端、前端與 spec 一致性檢查才能合併。

## Requirements

### Requirement: 後端與前端檢查
CI SHALL 在每個 PR 執行後端 lint 與測試、前端 build 與測試；任何一項失敗 MUST 讓 CI 失敗。push 到 `develop`/`main` 時才依目錄以 path filter 分開執行。

#### Scenario: 後端測試失敗
- **WHEN** PR 讓某個後端測試失敗
- **THEN** CI 失敗

### Requirement: Spec 一致性結構檢查
CI SHALL 在 PR 修改 `backend/`、`frontend/`、`db/`、`infra/` 卻沒有修改 `openspec/` 時失敗。

#### Scenario: 只改程式碼
- **WHEN** PR 只修改 `backend/app/main.py`
- **THEN** spec 檢查失敗

#### Scenario: 程式碼與 spec 一起改
- **WHEN** PR 同時修改 `backend/` 與 `openspec/changes/...`
- **THEN** spec 檢查通過

### Requirement: Terraform 檢查
CI SHALL 在每個 PR 執行 `terraform fmt -check` 與 `terraform validate`（不需要 AWS 憑證），任一失敗 MUST 讓 CI 失敗。

#### Scenario: 格式不符
- **WHEN** PR 中的 Terraform 檔案未經格式化
- **THEN** CI 失敗

### Requirement: 本機 commit 前檢查
Repo SHALL 提供 pre-commit 設定，在 commit 前執行行尾空白、檔尾換行、換行符號檢查，以及後端 `ruff check` 與 `ruff format --check`；任一失敗 MUST 擋下 commit。

#### Scenario: 後端 lint 錯誤
- **WHEN** 安裝 pre-commit 後 commit 一個超過行長度限制的後端檔案
- **THEN** commit 被擋下並顯示 ruff 錯誤

### Requirement: Proposal 與 spec delta 一致
CI SHALL 對 PR 修改到、已有 `specs/` 目錄且未標記 `skip_specs` 的 change，檢查 proposal「Capabilities」列出的每個 capability 都有 `specs/<capability>/spec.md`；缺少時 MUST 讓 CI 失敗並列出缺少的 capability。

#### Scenario: proposal 列了 capability 卻沒有 spec
- **WHEN** PR 修改的 change 的 proposal 列出 `input-guardrails`，但沒有 `specs/input-guardrails/spec.md`
- **THEN** spec 檢查失敗並指出 `input-guardrails`

#### Scenario: 尚未開工的 change
- **WHEN** PR 只修改一個沒有 `specs/` 目錄的 change 的 proposal
- **THEN** 不做 capability 檢查
