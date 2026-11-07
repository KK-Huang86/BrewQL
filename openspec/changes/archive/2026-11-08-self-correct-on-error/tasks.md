## 1. 後端

- [x] 1.1 測試 + 實作：Bedrock 產生器接受 `feedback`，以多輪訊息送出先前回覆與錯誤原因；驗證：以假 SDK client 的測試由紅轉綠
- [x] 1.1a 測試 + 實作：回饋只取第一行、最多 300 字、包在 `<error>` 標記並標明不是指令、`<` `>` 換成全形；驗證：測試由紅轉綠
- [x] 1.2 測試 + 實作：`QueryError` 區分逾時；`MAX_SQL_RETRIES` 設定（0～5，預設 1，同步 `.env.example`）；驗證：測試由紅轉綠
- [x] 1.3 測試 + 實作：流程重試（防護拒絕、執行錯誤、格式錯誤、用盡、0 次、逾時不重試、服務錯誤不重試、拒答不重試、重試中改為拒答、輸入 Guardrail 攔下為 0、`attempts`）；驗證：測試由紅轉綠
- [x] 1.4 測試 + 實作：失敗嘗試的 log（編號、類型、原因、SQL，不含問題）；驗證：測試由紅轉綠
- [x] 1.5 測試 + 實作：API 回應加入 `attempts`；驗證：測試由紅轉綠

## 2. 前端

- [x] 2.1 測試 + 實作：`attempts` 大於 1 時顯示「經過 N 次修正」；驗證：測試由紅轉綠

## 3. 端到端驗證

- [x] 3.1 以真實 Bedrock 問 5 個問題（含容易寫錯欄位的問題）並觀察 log；驗證：記錄每題 attempts，若有重試記錄錯誤原因
  - 結果（2026-11-08，Haiku 4.5、`MAX_SQL_RETRIES=1`、經 nginx）：8 題都沒有自然觸發重試，`attempts` 都是 1。台北市店數、工作友善比例（`ROUND(CAST(... AS DECIMAL), 2)`）、評分中位數與標準差：ok；各區前 3 名、每月新上架：clarify；收藏數（schema 尚無收藏表）、users 表、刪除：refused
  - 強制第一次失敗、第二次交給真實 Bedrock：欄位打錯（`nmae`，`UndefinedColumnError`）與白名單外的表（`users`，SQL 防護拒絕）都在第 2 次修正成功，`attempts=2`，被擋的 SQL 沒有執行；重試那次 input tokens 約 1,250，比一般約 1,110 多約 140（回饋內容）
  - 觀察：asyncpg 的錯誤字串第二行是 Postgres 的 `HINT`（例如 `Perhaps you meant "cafes.name"`），依 D6 只回饋第一行所以模型看不到，只有 log 保留；模型只靠第一行仍能修正
