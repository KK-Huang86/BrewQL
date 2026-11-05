## 1. 規則

- [x] 1.1 CLAUDE.md TDD 段落加入 red／green 分開 commit；驗證：新 session 讀 CLAUDE.md 即可得知
- [x] 1.2 CLAUDE.md PR 前一致性檢查改為 `openspec validate --strict`、`spectra drift`、`mattpocock-skills:code-review`；驗證：每個指令實際可執行

## 2. 自動檢查

- [x] 2.1 測試：`Settings` 每個欄位都出現在 `.env.example`；驗證：暫時刪掉一行時測試失敗（刪掉 `CORS_ORIGINS` → `add to .env.example: ['CORS_ORIGINS']`）

## 3. 本機整合測試

- [x] 3.1 `db/test-db.sh up|down`，CLAUDE.md 開發指令加入；驗證：`up` 後整合測試全過，`down` 後容器消失（10 個整合測試通過；以 process substitution 避開 `pipefail` 下 `grep -q` 提早關閉管線的問題）
