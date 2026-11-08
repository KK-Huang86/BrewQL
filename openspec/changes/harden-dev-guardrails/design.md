## Context

retro 的三個發現都是「人或 agent 會重複犯、程式能確定判斷」的錯，適合做成檢查而不是寫成提醒。

## Goals / Non-Goals

**Goals:** 錯的資料庫連線在送出密碼前擋下；lint 錯誤在 commit 前擋下；proposal 與 spec delta 不一致在 CI 擋下。

**Non-Goals:** 不檢查 API 本身的連線設定（compose 內固定連 `db:5432`）；pre-commit 不跑測試（太慢，CI 會跑）；不檢查 spec 內容是否符合程式碼（仍由 drift 與 code review 負責）。

## Decisions

### D1. 連線檢查放在評估，只看使用者與本機 port
評估是唯一在 compose 外、以 `.env` 連資料庫的入口。只解析 URL，不連線：使用者不是 `genbi_reader` 就擋（避免用擁有者帳號）；主機是本機（`localhost`、`127.0.0.1`、`::1`）時 port 必須等於 `DB_PORT`（未設定時為 5434，與 compose 預設相同）；URL 沒寫 port 時視為 Postgres 預設的 5432。`DB_PORT` 放在 `Settings`，和評估讀 `.env` 的方式一致；API 不使用它。其他主機（例如 CI 或遠端）不檢查 port。

### D2. 本機預設 port 5434
開發者本機常有其他 Postgres 佔 5432；BrewQL 固定用 5434，範本、compose 預設與文件一致，照範本填就不會撞到。

### D3. pre-commit 只放快的檢查
通用檔案檢查（`pre-commit-hooks`）加上後端 ruff（`language: system`，用專案的 `uv` 與 ruff 版本，與 CI 一致）。不跑 pytest、前端 lint。

### D4. capability 檢查只看這次 PR 動到、且已有 `specs/` 的 change
尚未開始的 ticket 只有 proposal，spec 在開工時才寫；只檢查已經寫 spec 的 change，避免擋下排程用的 proposal。capability 名稱從 proposal「## Capabilities」段落的 `` - `name`: `` 項目讀取。`skip_specs: true` 的 change 不檢查。

## Risks / Trade-offs

- [有人刻意用其他使用者跑評估] → 目前只有 `genbi_reader` 是合理選擇；真的需要時再加參數
- [pre-commit 沒安裝就不會跑] → CI 仍有 ruff 與 spec 檢查兜底
