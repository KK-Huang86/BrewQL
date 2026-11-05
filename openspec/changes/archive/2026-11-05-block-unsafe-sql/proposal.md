## Why

ticket 1 只擋「不是單一 SELECT」的 SQL。LLM 可能被 prompt injection 誘導去讀系統資料表、讀取識別欄位、呼叫 `pg_sleep` 拖住資料庫、或一次撈出大量資料。在加入更多資料表之前，要先補齊四層防護並用惡意輸入實際驗證。

## What Changes

- 靜態驗證補齊：CTE 內的資料修改、資料表白名單、非 public schema、封鎖識別欄位、危險函式、`SELECT ... INTO`
- 執行限制：強制回傳筆數上限（預設 1000）、statement timeout（預設 5 秒）
- 畫面清楚顯示「為什麼被擋」
- 以真實資料庫與 API 執行惡意輸入測試

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

- `sql-guardrails`: 新增白名單、敏感欄位、危險函式、筆數上限、逾時等需求。
- `query-web-ui`: 新增防護拒絕時的顯示方式。

## Impact

- 修改：`backend/app/sql_guard.py`、`backend/app/db.py`、設定、測試；`db/init` 唯讀角色加上 timeout；前端錯誤樣式
- 依賴 ticket：`ask-first-question`
