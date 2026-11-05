## Context

動機見 proposal.md。這是第一個打通所有層的 ticket，後續 12 個 ticket 都建立在它的結構上，所以這裡的決策會影響整個專案。開發者熟悉 Python／Django，對 React + TypeScript 與 Bedrock 較陌生。

## Goals / Non-Goals

**Goals:** 每一層都用最簡單、但之後不需要重寫的做法；各層之間以介面隔開，方便測試與替換。

**Non-Goals:** 效能、擴展性、完整防護（ticket 2）、正確率（ticket 5 開始量化）。

## Decisions

### D1. Monorepo，資料夾分層
`backend/`、`frontend/`、`db/`、`infra/` 同一個 repo。單人開發、前後端合約常一起改，一個 PR 就能保持一致。
- 實作時修正：CI 在**每個 PR** 都跑 backend、frontend、spec-check，只有 push 到 `develop`/`main` 才用 path filter。原因：三者是 branch protection 的必要檢查，PR 上被 path filter 跳過的 workflow 不會回報狀態，會讓 PR 永遠無法合併；也避免「改 A 弄壞 B」沒被測到。

### D2. 流程用一般 async 函式，依賴以 Protocol 注入
「產生 SQL」與「執行 SQL」各定義一個介面，流程只依賴介面；測試注入假物件，不呼叫真實 Bedrock 或資料庫。等加入 RAG、步驟推送等分支時再評估是否換 LangGraph。

### D3. Bedrock：`anthropic[bedrock]` SDK + `asyncio.to_thread`
使用 Anthropic SDK 的 Bedrock client（介面與官方文件一致），模型 ID 形如 `anthropic.claude-haiku-5-5`，推理強度預設 low。SDK 為同步呼叫，以 `asyncio.to_thread` 執行：等待網路時 GIL 會釋放，不會卡住事件迴圈。
- 替代方案：boto3 Converse API → 可用，但與官方範例差異大。
- 實作時修正：effort 只有 Claude 4.6 以後的模型支援，Haiku 4.5 傳入會回 400；改為由 `BEDROCK_EFFORT` 設定，留空就不送。帳號目前無法使用 Haiku 5.5，端到端驗證以 Haiku 4.5 US 推論設定檔進行；開通後只需改 `.env`。
- client 逾時 15 秒、重試 2 次：最壞約 45 秒，短於 nginx 的 60 秒，避免前端已斷線、後端還在等。

### D4. 模型回覆用 structured outputs（JSON schema）
以 Messages API 的 structured outputs 指定回覆的 JSON schema（本 ticket 只有 `sql`），由 API 保證格式，不需要從文字中解析程式碼區塊。ticket 3 再擴充成「SQL / 拒答 / 反問」三種結果。
- 替代方案：要求模型把 SQL 放在 ```` ```sql ```` 區塊再用正規表示式取出 → 模型偶爾不遵守格式，需要額外的錯誤處理。
- 若 Bedrock 上的模型版本不支援 structured outputs，改用 `strict: true` 的單一 tool 取得相同保證，並記錄在 tasks。

### D5. 防護分兩層先做
本 ticket 只做 sqlglot 驗證「單一 SELECT」與資料庫唯讀角色 + read-only transaction。真正的安全邊界是資料庫角色，所以第一天就要有；其他規則由 ticket 2 補齊。
- 實作時提前：唯讀角色的 `statement_timeout 5s` 與 `CONNECTION LIMIT 20` 在建立角色時一併設定（原屬 ticket 2），成本極低且避免第一版就能被慢查詢拖垮。

### D6. 資料庫：asyncpg + 延遲建立連線池
asyncpg 原生 async；第一次查詢才建立連線池，讓服務與測試在沒有資料庫時也能啟動。用 prepared statement 取得欄位名稱，空結果也有欄位。
- 錯誤分兩類：連不上（`DatabaseUnavailable`，API 回 503）與查詢被拒（`QueryError`，回 `status=error` + 通用訊息，原始錯誤只進 log；ticket 4 自我修正會用到原始錯誤）。服務關閉時由 lifespan 關閉連線池。

### D7. Demo 資料用純 SQL 產生
`generate_series` + `setseed` 放在 Postgres 的 init 目錄，首次啟動自動執行。

### D8. 前端：Vite + React + TypeScript，先不用 UI 元件庫
單一頁面用少量 CSS。API client 與送出控制寫成可單元測試的函式，Vitest + React Testing Library 測試。部署時由 nginx 提供靜態檔並把 `/api` 轉發到 backend，同網域不需處理正式環境的 CORS。

### D9. spec 檢查用 git diff 判斷
CI 比較 PR 與 base branch 的變更路徑；有程式碼目錄變更卻沒有 `openspec/` 變更就失敗。純粹的結構檢查，不做語意判斷。

### D10. 錯誤記錄
Bedrock 失敗時，產生器記一行（含模型 ID 與錯誤）後往外拋，API 層記一次完整錯誤追蹤並回 502；同一個錯誤不重複輸出 traceback。log 格式含時間與等級。

## Risks / Trade-offs

- [Bedrock 權限尚未開通] → 單元測試不依賴；smoke 腳本與瀏覽器 Demo 在開通後執行
- [ticket 範圍比其他 ticket 大] → 已有後端初稿；若超過 8 小時，把 CI 與 spec 檢查拆成獨立 ticket
- [React 不熟] → 頁面只做輸入框、表格、錯誤訊息
- [只允許單一 SELECT 仍可能查到不該看的資料表] → Demo 資料庫此時只有 `cafes`；ticket 2 加白名單
