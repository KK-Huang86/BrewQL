## Why

只有搜尋資料還看不到「使用者找到之後做了什麼」。加入瀏覽與收藏，才能回答轉換率、熱門店家、評分與收藏落差等問題，也讓資料表結構完整對應 Find Coffee，展示需要 JOIN 的較難問題。

## What Changes

- 新增模擬資料：`cafe_nomad_cache`（社群評分）、`cafe_attribute_votes`、`cafe_views`（約 20 萬筆，來源 search／favorite／rich_menu）、`favorites`
- 新增 view `v_cafe_profile`（咖啡店 + 社群評分 + 城市行政區）；`v_daily_activity` 加入瀏覽數與新增收藏數
- 兩個故事：從搜尋進入的瀏覽收藏轉換率較高；部分高評分店收藏很少
- schema 說明加入「收藏轉換率」「工作友善」「活躍使用者」定義
- 黃金測試集加入相關題目

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

- `demo-dataset`: 新增瀏覽、收藏、社群評分資料、`v_cafe_profile` 與兩個故事。
- `query-pipeline`: schema 說明涵蓋所有資料表與商業名詞。
- `evaluation`: 加入瀏覽與收藏相關題目。

## Impact

- 修改：`db/init`、白名單、schema 說明
- 依賴 ticket：`search-trend-line-chart`
