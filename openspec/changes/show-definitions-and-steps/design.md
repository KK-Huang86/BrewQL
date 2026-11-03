## Context

流程目前是一般 async 函式，一次回傳最終結果。

## Goals / Non-Goals

**Goals:** 即時步驟、斷線即取消、評估與既有端點不受影響。

**Non-Goals:** 逐字串流模型輸出、WebSocket、多輪對話。

## Decisions

### D1. SSE 而非 WebSocket
只需要伺服器單向推送，SSE 是一般 HTTP，實作與部署（nginx）都較簡單。

### D2. 流程改寫為 LangGraph
到這個 ticket，流程已有輸入防護、檢索、產生、驗證、執行、重試、拒答、反問等分支，自己寫的迴圈與 if 開始難讀。改成 LangGraph：
- 每個步驟是一個 async 節點（節點內仍使用 `asyncio.gather`、`to_thread`、asyncpg）
- 重試、拒答、反問以條件邊表達，重試上限放在 graph state
- `ainvoke` 一次跑完（評估與 `/api/ask` 使用）；`astream` 逐步產出節點事件（SSE 使用），不需要自己做事件回呼與 Queue

這是重構：先保留既有流程的所有測試，改寫後必須全部通過（測試不可為了配合 LangGraph 而修改），再加入步驟事件的新測試。
- 替代方案：保留一般函式並加事件回呼 → 可行，但分支越多越難維護，也無法展示 JD 要求的 LangGraph。

### D3. 斷線取消
流程放在獨立的 task 執行；偵測到客戶端斷線時 cancel 該 task。`to_thread` 中正在進行的 Bedrock 呼叫無法中斷，但結束後不會再進入下一步。

### D4. 前端用 GET + EventSource
瀏覽器原生 `EventSource` 只支援 GET，問題以 query string 傳遞（上限 1000 字元在 URL 長度內）。nginx 對該路徑關閉 buffering。
- 替代方案：POST + fetch 讀取串流 → 需自行解析 SSE 格式。

### D5. 評估不經過串流
評估繼續用 `/api/ask` 等價的函式，不經串流，避免影響延遲數據。

## Risks / Trade-offs

- [nginx 預設 buffering 讓步驟一次全部出現] → 對串流路徑設定 `proxy_buffering off`
- [Bedrock 呼叫無法中途取消] → 接受，最多浪費一次呼叫
