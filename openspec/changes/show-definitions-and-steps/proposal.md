## Why

可信度來自「看得到依據」與「看得到過程」。回答引用了哪個名詞定義，使用者應該點得開；一個問題要 5～15 秒，畫面應該即時顯示系統正在做什麼，而不是只有轉圈圈。

## What Changes

- 畫面列出本次回答使用的知識（名詞定義、欄位說明、範例），可點開查看全文
- 流程改寫為 **LangGraph** 圖（節點：輸入防護、檢索、產生、驗證、執行；條件邊：重試、拒答、反問），既有行為與測試不變
- 新增串流端點，以 SSE 即時推送處理步驟：檢索知識、產生 SQL、驗證、執行（含重試）、完成
- 使用者關閉頁面或取消時，後端停止處理
- 原本的 `/api/ask` 保留（評估使用）

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

- `query-pipeline`: 流程可對外回報步驟事件、可被取消。
- `query-api`: 新增串流提問端點與知識全文查詢端點。
- `query-web-ui`: 新增步驟即時顯示與知識來源面板。

## Impact

- 修改：流程改為 LangGraph（步驟事件、取消）、API、前端
- 新依賴：langgraph
- 依賴 ticket：`rag-knowledge-base`
