## Context

ticket 6、7 已有會員、搜尋紀錄與行政區供需落差，但只看得到「搜尋」，看不到使用者找到店之後做了什麼。真實 Find Coffee 的 `cafes` 有 `favorite_count`、`view_count`，另有屬性投票 `cafe_cafeattributevote` 與 Cafe Nomad 社群資料 `cafe_nomad_cache`（欄位已由 2026-11-08 的本機匯出檔確認，見 `import-real-cafes` proposal）。這個 ticket 補上瀏覽與收藏，並以真實匯出檔的欄位為準建立示範表，讓之後的 `import-real-cafes` 可以直接套用。

這也是加入 RAG（ticket 9）之前最後一個擴充資料的 ticket，完成後的評估結果就是 RAG 的比較基準。

## Goals / Non-Goals

**Goals:**
- 問「從搜尋進入和從選單進入，哪個收藏轉換率比較高？」得到兩列的長條圖，搜尋較高。
- 問「評分 4.7 以上但收藏很少的店」得到幾家店。
- 需要 JOIN 的題目（社群評分 + 店家屬性、瀏覽 + 收藏）可以回答。

**Non-Goals:**
- 新的圖表類型；現有的長條圖、數字卡、表格已足夠。
- 店家詳細頁、使用者路徑（漏斗）分析。
- 匯入真實資料（`import-real-cafes`）。

## Decisions

### D1. 示範表以真實匯出檔為準，只取回答問題需要的欄位
- `cafes` 加 `favorite_count`、`view_count`（真實表已有）。
- `cafe_nomad_cache`：`cafenomad_id`、`name`、`wifi`、`seat`、`quiet`、`tasty`、`cheap`、`music`（0～5 分，可為 NULL）、`socket`、`limited_time`、`standing_desk`（yes/maybe/no）、`mrt`、`synced_at`。
  真實表沒有 `cafe_id`，靠店名＋座標比對；示範表直接加 `cafe_id`（UNIQUE），代表「已比對成功」，約 70% 的店有一列。比對的工作留給 `import-real-cafes`。
- `cafe_attribute_votes`：`cafe_id`、`attribute`、`value`、`source`（google／cafenomad／user）、`created_at`。
  **不含 `user_id`**：真實匯出的 user 來源投票帶真實使用者 id，`import-real-cafes` 已決定只匯入不含 `user_id` 的資料；示範表採用同一個結構，兩種資料集的 schema 說明才會一致。
- 不建地址、電話、營業時間、評論、照片等欄位，問題用不到。

### D2. 瀏覽與收藏
- `cafe_views`：`user_id`、`cafe_id`、`source`、`created_at`，約 200,000 筆。`source`：`search`（從搜尋結果點進）、`favorite`（從收藏清單點進）、`rich_menu`（從 LINE 選單點進）。
- `favorites`：`user_id`、`cafe_id`、`source`、`created_at`，`UNIQUE (user_id, cafe_id)`。`source` 是按下收藏時所在的入口，只有 `search` 或 `rich_menu`（從收藏清單進入的店已經收藏過）。
- 時間規則與搜尋相同：會員註冊後才有瀏覽，日期在建庫日往回 6 個月內。每筆收藏都有一筆**更早**、同會員同店同來源的瀏覽。
- `cafes.favorite_count`、`view_count` 由明細計算後寫回，與明細一致。

### D3. 收藏轉換率 = 該入口的收藏數 ÷ 該入口的瀏覽數
```sql
SELECT source,
       (SELECT count(*) FROM favorites f WHERE f.source = v.source)::numeric / count(*) AS rate
FROM cafe_views v WHERE source IN ('search', 'rich_menu') GROUP BY source
```
考慮過「瀏覽之後同會員同店有收藏才算轉換」的配對算法，比較精確，但需要多條件 JOIN 與時間比較，模型容易寫錯，故事檢查也難對齊。收藏帶 `source` 讓定義只剩兩個計數相除，仍需要兩張表（golden set 的 JOIN 題）。schema 說明、故事檢查、golden set 用同一個算法。

### D4. 名詞定義
- 收藏轉換率：D3。
- 活躍使用者：指定期間內有搜尋或瀏覽紀錄的會員（去重）；未指定期間時用最近 30 天。和 `users.status = 'active'`（帳號使用中）不同，schema 說明兩者都寫清楚。
- 收藏很少／很多：問題沒給門檻時，以所有店 `favorite_count` 的中位數為界（`percentile_cont(0.5)`）。
- 工作友善、搜尋落空率、時間用語：沿用。

### D5. 故事
- 轉換率：`search` 約 12%，`rich_menu` 約 4%。搜尋代表使用者有明確需求，選單多半是隨意瀏覽。
- 高評分低收藏：固定挑 5 家 `rating >= 4.7` 的店壓低瀏覽與收藏，`favorite_count` 低於中位數（「評分高但沒人知道」）。其他店的收藏大致隨評分與評論數增加，讓這 5 家顯得突兀。

### D6. 新資料在既有資料之後產生
`02_seed.sql` 用固定 `setseed`；新資料表的 INSERT 放在 `search_logs` 之後，既有的店家、會員、搜尋的亂數順序不變，ticket 6、7 的故事檢查與 golden set 答案不受影響。`favorite_count`、`view_count` 以 UPDATE 寫回，不會改變既有欄位的值。

### D7. `v_cafe_profile` 與 `v_daily_activity`
- `v_cafe_profile`：`cafes` 全部欄位 LEFT JOIN `cafe_nomad_cache` 的評分欄位與 `mrt`；沒有社群評分的店仍在，評分欄為 NULL。
- `v_daily_activity` 加 `views`、`new_favorites`，沒有活動為 0，列數不變（仍從第一筆搜尋到今天）。
- schema 說明建議：店家屬性與社群評分一起問時優先用 `v_cafe_profile`，每日趨勢優先用 `v_daily_activity`。

## Risks / Trade-offs

- [20 萬筆瀏覽讓建庫變慢] → 用 `generate_series` 一次 INSERT，記錄初始化耗時；超過 30 秒再改寫法。
- [`favorites.source` 是示範資料自己加的欄位，真實表不一定有] → `import-real-cafes` 不匯入任何行為資料，收藏、瀏覽一律模擬，不衝突。
- [schema 說明變長，每題 input tokens 增加約 40%] → 3.3 的評估記錄成本變化；這正是 ticket 9 RAG 要解決的問題，留作比較基準。
- [`v_daily_activity` 加欄位可能改變模型對趨勢題的寫法] → 3.3 完整評估確認 q16～q21 沒有退步。
