## Why

「可信、可追溯」的核心是讓使用者看到系統實際執行的 SQL；覺得不對時能自己修改後重跑，而不是只能換個問法再問一次。這也是「需要人工確認」時的處理方式。

## What Changes

- 新增 `POST /api/sql`：執行使用者提供的 SQL，套用完全相同的防護，不經過模型
- 畫面顯示實際執行的 SQL，可編輯後按「重新執行」，以新結果取代畫面

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

- `query-api`: 新增執行 SQL 端點。
- `query-web-ui`: 新增檢視、修改、重新執行 SQL。

## Impact

- 修改：API、前端
- 依賴 ticket：`ask-first-question`（防護越完整越好，建議在 `block-unsafe-sql` 之後做）
