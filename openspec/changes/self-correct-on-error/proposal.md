## Why

模型常犯小錯：欄位名稱打錯、用了白名單外的資料表、語法不合 Postgres。這些錯誤的訊息本身就是修正線索。把錯誤回饋給模型重新產生，可以在不增加使用者負擔的情況下提高成功率；但重試必須有上限，避免成本與延遲失控。

## What Changes

- 防護拒絕或資料庫執行錯誤時，帶著錯誤訊息重新產生 SQL，最多重試設定次數（預設 2）
- 模型沒產生 SQL 也算一次失敗嘗試
- 回應加入 `attempts`；畫面顯示「經過 N 次修正」
- 每次失敗嘗試留下 log

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

- `query-pipeline`: 新增有上限的自動修正。
- `query-web-ui`: 新增修正次數顯示。

## Impact

- 修改：流程、Bedrock 產生器（接受錯誤回饋）、API 回應、前端
- 依賴 ticket：`block-unsafe-sql`（需要 `error_kind` 與完整防護訊息作為回饋）
