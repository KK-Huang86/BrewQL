## 1. 評估連線檢查

- [x] 1.1 測試 + 實作：評估開跑前檢查 `DATABASE_URL`（非 `genbi_reader`、本機 port 與 `DB_PORT` 不符、未設定 `DB_PORT` 時以 5434 比對、非本機主機不檢查 port、URL 空白），不符合時報錯結束且不建立連線；驗證：測試由紅轉綠
- [x] 1.2 本機預設 port 改為 5434、`AWS_PROFILE` 範本改為 `brewql`（`.env.example`、`docker-compose.yml`、README）；驗證：`docker compose config` 顯示 5434

## 2. 本機 commit 前檢查

- [ ] 2.1 新增 `.pre-commit-config.yaml`（pre-commit-hooks 三項 + 後端 ruff check／format）並設定 ruff `known-first-party`；驗證：`uvx pre-commit run --all-files` 通過

## 3. CI capability 檢查

- [ ] 3.1 測試 + 實作：`tools/spec_check.py` 檢查 PR 動到的 change（已有 `specs/`、非 `skip_specs`）proposal 列出的 capability 都有 spec delta；驗證：測試由紅轉綠，現有 change 全部通過
