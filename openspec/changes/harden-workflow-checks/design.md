## Context

retro（2026-11-09，ticket 7、8）的結論。repo 沒有 `CODING_STANDARDS.md`；所有規則都在每輪載入的 CLAUDE.md。`tools/spec_check.py` 已有 `_touched_changes()` 列出 PR 動到的 change。

## Goals / Non-Goals

**Goals:** 混入其他 change 的 PR 由 CI 擋下；實作時的 context 只帶必要的規則；突變測試一個指令完成。

**Non-Goals:** 改變 TDD 或 PR 前檢查的內容本身；檢查 commit 順序（red 在 green 前）。

## Decisions

### D1. 一個有程式碼的 PR 只動一個 change
條件是「PR 有 `backend/`、`frontend/`、`db/`、`infra/` 變更」且 `openspec/changes/<name>/` 的 `<name>`（排除 `archive`）超過一個。純文件 PR 不受限：例如 #21 同時規劃 `import-real-cafes` 與 `import-open-data` 是合理的。訊息列出動到的 change，提示把其他 change 的文件移到另一個分支。`openspec/specs/` 的主規格不算 change。

### D2. 規則依讀者分兩個檔
- CLAUDE.md（實作時每輪載入）：專案說明、技術棧、結構、指令、安全底線（唯讀角色、不繞過防護、不放真實使用者資料、不 commit secret、不呼叫外部服務的 unit test、IAM role）、分支與 commit 慣例、retro 提醒，以及一行指向 `CODING_STANDARDS.md`：「寫測試、改資料寫入路徑、準備開 PR 前先讀」。
- `CODING_STANDARDS.md`（review 必讀，實作時依指引讀）：TDD、資料操作穩健性、PR 前 spec 一致性檢查。內容原文搬移，規則只做以下兩處修改；另外在檔案開頭加一段「何時讀哪一節」的導覽，標題從 `#` 降為 `##`。
- CLAUDE.md 指令區補三個在 ticket 7、8 讓實作多試幾次的指令：評估 `--dry-run` 對測試資料庫（`DB_PORT` 要和 `DATABASE_URL` 一致）、`uv --directory backend` 的測試路徑相對 `backend/`、`mutate.sh`。

### D3. 資料操作穩健性加適用條件
服務本身唯讀，目前只有建庫 seed 寫入。8 條規則保留（ticket 11 稽核紀錄會寫入資料庫），標題下加「適用於新增或修改資料寫入路徑時（例如稽核紀錄、匯入腳本）。BrewQL 的查詢路徑是唯讀的；唯讀查詢與建庫 seed 只需遵守第 1、5 條」。

### D4. 修改既有測試的 commit
TDD 第 5 條補一句：因需求變更修改既有測試時，修改獨立成 `test:` commit 並放在 `feat:` 之前，讓歷史看得到舊測試在新需求下變紅。

### D5. `mutate.sh`
`db/checks/mutate.sh "<改資料的 SQL>" <檢查檔或 db/checks 下的檔名>`：把 `BEGIN; <SQL>; \echo <標記>; <檢查檔內容>; ROLLBACK;` 送進 `$PSQL`（與 `run.sh` 相同的環境變數）。

- 標記之後出現 `ERROR`：檢查抓到，印 `caught: <第一行 ERROR>` 並回傳 0。
- 標記之後沒有 `ERROR`：印 `NOT caught` 並回傳 1。
- 沒有標記（突變 SQL 本身失敗或 psql 連不上）、參數錯誤：回傳 2。review 發現只看 `ERROR` 會把突變 SQL 的錯字誤判成 caught，所以用標記分開。

不管結果都不會留下變更：rollback 在同一個 session，`ON_ERROR_STOP` 中斷時連線結束也會 rollback；`ROLLBACK` 前補換行，避免檢查檔最後一行是沒有換行的註解時把它吃掉。

## Risks / Trade-offs

- [實作時沒讀 `CODING_STANDARDS.md` 就寫測試] → CLAUDE.md 的導覽寫明觸發時機；review 一定讀，漏掉的會在 review 抓到
- [D1 擋下合理的跨 change 程式碼 PR] → 目前沒有這種需要；真的需要時拆成兩個 PR
