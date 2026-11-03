## Context

動機見 proposal.md。這是第一個打通所有層的 ticket，後續 12 個 ticket 都建立在它的結構上，所以這裡的決策會影響整個專案。開發者熟悉 Python／Django，對 React + TypeScript 與 Bedrock 較陌生。

## Goals / Non-Goals

**Goals:** 每一層都用最簡單、但之後不需要重寫的做法；各層之間以介面隔開，方便測試與替換。

**Non-Goals:** 效能、擴展性、完整防護（ticket 2）、正確率（ticket 5 開始量化）。

## Decisions

### D1. Monorepo，資料夾分層
`backend/`、`frontend/`、`db/`、`infra/` 同一個 repo，CI 依目錄以 path filter 分開執行。單人開發、前後端合約常一起改，一個 PR 就能保持一致。

### D2. 流程用一般 async 函式，依賴以 Protocol 注入
「產生 SQL」與「執行 SQL」各定義一個介面，流程只依賴介面；測試注入假物件，不呼叫真實 Bedrock 或資料庫。等加入 RAG、步驟推送等分支時再評估是否換 LangGraph。

### D3. Bedrock：`anthropic[bedrock]` SDK + `asyncio.to_thread`
使用 Anthropic SDK 的 Bedrock client（介面與官方文件一致），模型 ID 形如 `anthropic.claude-haiku-5-5`，推理強度預設 low。SDK 為同步呼叫，以 `asyncio.to_thread` 執行：等待網路時 GIL 會釋放，不會卡住事件迴圈。
- 替代方案：boto3 Converse API → 可用，但與官方範例差異大。

### D4. 模型回覆用 structured outputs（JSON schema）
以 Messages API 的 structured outputs 指定回覆的 JSON schema（本 ticket 只有 `sql`），由 API 保證格式，不需要從文字中解析程式碼區塊。ticket 3 再擴充成「SQL / 拒答 / 反問」三種結果。
- 替代方案：要求模型把 SQL 放在 ```` ```sql ```` 區塊再用正規表示式取出 → 模型偶爾不遵守格式，需要額外的錯誤處理。
- 若 Bedrock 上的模型版本不支援 structured outputs，改用 `strict: true` 的單一 tool 取得相同保證，並記錄在 tasks。

### D5. 防護分兩層先做
本 ticket 只做 sqlglot 驗證「單一 SELECT」與資料庫唯讀角色 + read-only transaction。真正的安全邊界是資料庫角色，所以第一天就要有；其他規則由 ticket 2 補齊。

### D6. 資料庫：asyncpg + 延遲建立連線池
asyncpg 原生 async；第一次查詢才建立連線池，讓服務與測試在沒有資料庫時也能啟動。用 prepared statement 取得欄位名稱，空結果也有欄位。

### D7. Demo 資料用純 SQL 產生
`generate_series` + `setseed` 放在 Postgres 的 init 目錄，首次啟動自動執行。

### D8. 前端：Vite + React + TypeScript，先不用 UI 元件庫
單一頁面用少量 CSS。API client 與送出控制寫成可單元測試的函式，Vitest + React Testing Library 測試。部署時由 nginx 提供靜態檔並把 `/api` 轉發到 backend，同網域不需處理正式環境的 CORS。

### D9. spec 檢查用 git diff 判斷
CI 比較 PR 與 base branch 的變更路徑；有程式碼目錄變更卻沒有 `openspec/` 變更就失敗。純粹的結構檢查，不做語意判斷。

## Risks / Trade-offs

- [Bedrock 權限尚未開通] → 單元測試不依賴；smoke 腳本與瀏覽器 Demo 在開通後執行
- [ticket 範圍比其他 ticket 大] → 已有後端初稿；若超過 8 小時，把 CI 與 spec 檢查拆成獨立 ticket
- [React 不熟] → 頁面只做輸入框、表格、錯誤訊息
- [只允許單一 SELECT 仍可能查到不該看的資料表] → Demo 資料庫此時只有 `cafes`；ticket 2 加白名單
