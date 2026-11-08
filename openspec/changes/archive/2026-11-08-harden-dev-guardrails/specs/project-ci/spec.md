## ADDED Requirements

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
