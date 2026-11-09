## ADDED Requirements

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
