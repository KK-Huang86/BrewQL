## Why

retro（self-correct-on-error、eval-golden-set）找出三個可以自動擋下的問題：

1. 本機設定範本把 agent 帶向錯的資料庫與錯的 AWS 身分：`.env.example` 的 `DB_PORT=5432` 撞到本機其他專案的 Postgres，評估試跑時把 `genbi_reader` 的密碼送到那個 Postgres 兩次；`AWS_PROFILE=default` 是其他專案的使用者。
2. lint 錯誤要等 commit 後、甚至 CI 才發現，紅燈 commit 因此要 amend；ruff 沒設定 first-party 套件，新模組建立前會被當成第三方排序。
3. proposal 列出的 capability 沒有對應的 spec delta（eval-golden-set 的 `input-guardrails`），要等 code review 才抓到；這是固定規則，程式就能檢查。

## What Changes

- 評估開跑前（含試跑）檢查 `DATABASE_URL`：使用者必須是 `genbi_reader`；連本機（`localhost`／`127.0.0.1`）時 port 必須等於 `DB_PORT`。不符合就報錯結束，不建立連線
- 本機預設 port 改為 5434：`.env.example`、`docker-compose.yml` 預設值、README；`.env.example` 的 `AWS_PROFILE` 改為 `brewql`
- 新增 pre-commit：行尾空白、檔尾換行、換行符號統一，以及後端 `ruff check`、`ruff format --check`
- ruff 設定 `known-first-party = ["app", "evaluation", "scripts"]`
- CI spec 檢查新增：PR 修改到的 change 若已有 `specs/`，proposal「Capabilities」列出的每個 capability 都必須有 `specs/<capability>/spec.md`

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

- `project-ci`: 本機 commit 前檢查；proposal 與 spec delta 一致的結構檢查。
- `evaluation`: 開跑前檢查資料庫連線設定。

## Impact

- 修改：`backend/evaluation/`、`tools/spec_check.py`、`.github/workflows/spec-check.yml`、`backend/pyproject.toml`、`.env.example`、`docker-compose.yml`、README
- 新增：`.pre-commit-config.yaml`
- 已經有 `.env` 的人：自己的 `DB_PORT` 與 `DATABASE_URL` 不受影響；沒設 `DB_PORT` 的人 compose 會改用 5434
- pre-commit 需要各自安裝一次（`uvx pre-commit install`）
