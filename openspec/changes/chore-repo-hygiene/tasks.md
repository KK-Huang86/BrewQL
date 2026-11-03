## 1. 清理追蹤檔案

- [x] 1.1 以 `git rm --cached` 移除 `.DS_Store`、`.idea/`，刪除 `main.py`；驗證：`git ls-files` 不含這三者，本機 `.idea/` 仍存在（已有初稿）
- [x] 1.2 檢查第一個 commit 的檔案內容是否含 secrets；驗證：`git show --stat e38f4f1` 與內容檢查結果記錄在任務說明中

## 2. .gitignore

- [x] 2.1 改寫 `.gitignore`（OS/IDE、`.env*` 與 `!.env.example`、Python、Node、Terraform、資料 dump、`eval/results/`）；驗證：建立 `.env`、`x.tfstate`、`node_modules/a` 測試檔後 `git status` 不顯示它們，`.env.example` 會顯示（已有初稿）

## 3. CLAUDE.md

- [x] 3.1 改寫專案概述、技術棧、monorepo 結構、開發指令、注意事項為 genbi 內容；驗證：全文不再出現 Django、LINE Bot、Celery 等 Find Coffee 專屬描述
- [x] 3.2 保留 TDD、資料操作穩健性、PR 前 spec 一致性檢查三段規則，移除指向 Find Coffee repo 的 Agent skills 段落；驗證：與原文 diff 確認三段規則內容未被改動
