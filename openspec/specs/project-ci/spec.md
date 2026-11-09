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

### Requirement: 一個有程式碼的 PR 只實作一個 change
CI SHALL 在 PR 修改 `backend/`、`frontend/`、`db/`、`infra/`，且修改到 `openspec/changes/` 下超過一個 change（`archive/` 不算）時失敗，並列出動到的 change。只修改文件的 PR 不受此限。

#### Scenario: 程式碼 PR 混入另一個 change
- **WHEN** PR 修改 `backend/app/charts.py`、`openspec/changes/district-gap-bar-chart/tasks.md` 與 `openspec/changes/import-real-cafes/proposal.md`
- **THEN** spec 檢查失敗並列出 `district-gap-bar-chart`、`import-real-cafes`

#### Scenario: 文件 PR 規劃多個 change
- **WHEN** PR 只修改 `openspec/changes/import-real-cafes/proposal.md` 與 `openspec/changes/import-open-data/proposal.md`
- **THEN** spec 檢查通過

#### Scenario: 實作同時 archive
- **WHEN** PR 修改 `db/init/02_seed.sql`、`openspec/changes/view-favorite-insights/tasks.md` 與 `openspec/changes/archive/2026-11-09-district-gap-bar-chart/tasks.md`
- **THEN** spec 檢查通過

### Requirement: 故事檢查的突變工具
Repo SHALL 提供 `db/checks/mutate.sh`，在同一個交易中套用改資料的 SQL、執行指定的故事檢查並 rollback；檢查抓到時回報第一行錯誤並成功結束，沒抓到時回報 `NOT caught` 並失敗。突變 SQL 本身失敗 MUST NOT 被當成檢查抓到。

#### Scenario: 檢查抓到突變
- **WHEN** 突變讓檢查 `RAISE EXCEPTION`
- **THEN** 印出 `caught:` 與錯誤訊息，結束碼為 0

#### Scenario: 檢查沒抓到突變
- **WHEN** 突變後檢查仍然通過
- **THEN** 印出 `NOT caught`，結束碼為 1

#### Scenario: 一定 rollback
- **WHEN** 執行任何突變
- **THEN** 送給資料庫的指令以 `BEGIN` 開頭、以 `ROLLBACK` 結尾

#### Scenario: 突變 SQL 本身失敗
- **WHEN** 突變 SQL 引用不存在的欄位，檢查還沒執行就出錯
- **THEN** 不印 `caught`，結束碼為 2
