## Why

BI 的價值在「看出變化」。目前只有咖啡店主檔，問不出趨勢。加入模擬的搜尋紀錄，並刻意設計「考試季效應」，讓營運人員問「最近半年不限時的搜尋量趨勢」時能看到一張有高峰的折線圖。這也是第一次需要「依結果自動選圖表」。

## What Changes

- 新增模擬資料：`users`（約 2,000 位，無任何 LINE 識別資訊）、`search_logs`（約 5 萬筆、建庫當天往回 6 個月），內建考試季效應
- 新增 view `v_daily_activity`（每日搜尋數、新會員數，無活動補 0）
- 白名單與唯讀角色加入新資料表與 view；schema 說明加入欄位與名詞（時間用語）
- 新增圖表選擇：日期（含 `YYYY-MM`、`YYYY-MM-DD` 文字）+ 數值 → 折線圖，其他 → 表格
- 畫面以 Recharts 畫折線圖
- 黃金測試集加入趨勢題

## Capabilities

### New Capabilities

- `result-visualization`: 依查詢結果形狀決定圖表。

### Modified Capabilities

- `demo-dataset`: 新增使用者、搜尋紀錄、每日活動 view 與考試季故事。
- `input-guardrails`: 拿掉 off-topic 拒絕話題，只保留 prompt attack 偵測；無關問題由模型拒答。
- `query-api`: `/api/ask` 回應加入 `chart`。
- `query-web-ui`: 新增折線圖。
- `evaluation`: 黃金測試集加入趨勢題。

## Impact

- 修改：`infra/terraform/guardrail.tf`（拿掉拒絕話題，需要以 `brewql-deployer` apply 並更新 `BEDROCK_GUARDRAIL_VERSION`）、`db/init`、白名單設定、schema 說明、流程回應加入 `chart`、前端
- 新依賴：recharts
- 依賴 ticket：`eval-golden-set`
