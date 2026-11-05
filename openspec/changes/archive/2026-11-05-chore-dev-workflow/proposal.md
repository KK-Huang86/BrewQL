## Why

第一次 retro（`ask-first-question`、`block-unsafe-sql` 之後）發現：嚴格 TDD 的 commit 規則只存在對話中、CLAUDE.md 指向不存在的 `/spectra-verify`、`.env.example` 漏同步要靠 code review 才發現、本機整合測試每次都要手動架 Postgres。

## What Changes

- CLAUDE.md：寫入「每個 TDD 循環先 commit `(red)` 再 commit `(green)`」；PR 前一致性檢查改為實際可用的指令
- 新增測試：`Settings` 每個欄位都必須出現在 `.env.example`
- 新增 `db/test-db.sh`：一個指令啟動／關閉已初始化的測試 Postgres（CI 同一組測試密碼）
- 不改變任何系統行為（`skip_specs: true`）

## Capabilities

### New Capabilities

（無，開發流程與工具）

### Modified Capabilities

（無）

## Impact

- 修改：`CLAUDE.md`、`backend/tests/`；新增 `db/test-db.sh`
