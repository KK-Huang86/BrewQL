## Why

只有搜尋資料還看不到「使用者找到之後做了什麼」。加入瀏覽與收藏，才能回答轉換率、熱門店家、評分與收藏落差等問題，也讓資料表結構完整對應 Find Coffee，展示需要 JOIN 的較難問題。完成後的評估結果是加入 RAG 之前的最終基準。

## What Changes

- `cafes` 加 `favorite_count`、`view_count`，與明細一致
- 新增模擬資料，欄位以真實 Find Coffee 匯出檔為準：
  - `cafe_nomad_cache`（社群評分，約 70% 的店有資料）
  - `cafe_attribute_votes`（屬性投票，不含 `user_id`）
  - `cafe_views`（約 20 萬筆，來源 search／favorite／rich_menu）
  - `favorites`（同會員同店最多一筆，記錄收藏時的入口）
- 新增 view `v_cafe_profile`（咖啡店 + 社群評分）；`v_daily_activity` 加入瀏覽數與新增收藏數
- 兩個故事：從搜尋進入的收藏轉換率較高；部分高評分店收藏很少
- 唯讀角色授權與 SQL 白名單加入新資料表與 view
- schema 說明補齊新資料表，加入「收藏轉換率」「活躍使用者」「收藏很少」定義
- 黃金測試集加入 5 題（q22～q26）

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

- `demo-dataset`: 新增瀏覽、收藏、社群評分、屬性投票資料、`v_cafe_profile` 與兩個故事。
- `sql-guardrails`: 白名單加入新資料表與 view。
- `query-pipeline`: schema 說明涵蓋所有資料表與商業名詞。
- `evaluation`: 加入瀏覽與收藏相關題目。

## Impact

- 修改：`db/init`（schema、seed、唯讀角色）、`db/checks`、`backend/app/sql_guard.py`、`backend/app/schema_context.py`、`backend/evaluation/golden.yaml`
- Demo 資料庫需重建（`docker compose down -v`）
- 依賴 ticket：`district-gap-bar-chart`
