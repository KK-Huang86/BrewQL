## Why

Repo 目前追蹤了不該上 GitHub 的檔案（`.DS_Store`、`.idea/`、PyCharm 範例 `main.py`），`.gitignore` 沿用 Find Coffee 的設定、缺少前端與 Terraform 規則，CLAUDE.md 也還在描述 Find Coffee。在開始寫任何功能前先把基礎整理乾淨，避免敏感檔案或雜訊進入版本歷史。

## What Changes

- 從 git 追蹤中移除 `.DS_Store`、`.idea/`，刪除 IDE 範例 `main.py`
- 改寫 `.gitignore`：涵蓋 OS/IDE、`.env*`（保留 `.env.example`）、Python、Node、Terraform state/變數、資料 dump、評估輸出
- 改寫 `CLAUDE.md` 為 genbi 專案說明（概述、技術棧、monorepo 結構、開發指令、注意事項），保留 TDD、資料操作穩健性、PR 前 spec 一致性檢查三段共用規則
- 不改變任何系統行為（`skip_specs: true`）

## Capabilities

### New Capabilities

（無，純 repo 整理與文件）

### Modified Capabilities

（無）

## Impact

- 影響檔案：`.gitignore`、`CLAUDE.md`、`.DS_Store`、`.idea/`、`main.py`
- 本機的 `.idea/` 與 `.DS_Store` 檔案保留，只是不再被 git 追蹤
- 第一個 commit（`e38f4f1`）中已含 `.DS_Store` 與 `.idea/.gitignore`，內容不含敏感資訊，不需改寫 git 歷史
