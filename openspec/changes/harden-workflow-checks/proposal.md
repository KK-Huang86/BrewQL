## Why

ticket 7、8 的 retro 找到三個執行層面的問題：

- ticket 7 的 feature 分支混進另外兩個 change 的文件，code review 才抓到，必須 cherry-pick 加 rebase 搬走。這條規則看路徑就能判斷，應該由 CI 擋下。
- CLAUDE.md 每一輪都載入，但約七成是 review 時才用到的規則（TDD 細則、資料操作穩健性、PR 前檢查）；資料操作穩健性的 8 條在唯讀服務裡大多用不到。
- 三個指令讓實作多試了幾次：對測試資料庫跑評估 `--dry-run`、`uv --directory backend` 的測試路徑、故事檢查的突變測試。

## What Changes

- `tools/spec_check.py`：有程式碼變更的 PR，`openspec/changes/` 底下只能動到一個 change（`archive/` 不算）；純文件 PR 不受限
- 新增 `db/checks/mutate.sh`：在交易中套用一段改資料的 SQL、執行一個故事檢查、一定 rollback，回報檢查有沒有抓到
- 新增 `CODING_STANDARDS.md`：review 用的規則（TDD、資料操作穩健性、PR 前 spec 一致性檢查）從 CLAUDE.md 搬過來；資料操作穩健性加上適用條件；補「因需求變更修改既有測試要獨立 `test:` commit」
- CLAUDE.md 只留專案說明、指令、安全底線與指向 `CODING_STANDARDS.md` 的導覽；指令區補上述三個指令

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

- `project-ci`: spec 檢查加上「一個有程式碼的 PR 只實作一個 change」；新增故事檢查的突變工具。

## Impact

- 修改：`tools/spec_check.py`、`CLAUDE.md`
- 新增：`CODING_STANDARDS.md`、`db/checks/mutate.sh`、`tools/test_one_change_check.py`、`tools/test_mutate.py`
- 不改變 API、資料或模型行為
