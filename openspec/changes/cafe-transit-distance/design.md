## Context

動機見 proposal.md。`youbike_stations`、`mrt_stations` 已有 `lat`、`lng`（`NUMERIC(9, 6)`）。real 匯入的 `CafeRow` 已經讀入 `lat`、`lng`，只是不寫入資料庫（import-real-cafes D4）。demo 店家由 `db/init/demo/02_seed.sql` 以 `setseed(0.42)` 產生，在公開資料載入（`06_open_data.sh`）之前執行。

## Goals / Non-Goals

**Goals:** 每家店都有座標；模型以一個 view 回答距離問題，不必自己寫距離公式；demo 的既有資料與評估答案不變。

**Non-Goals:** 步行路徑、PostGIS、出入口距離。

## Decisions

### D1. 欄位
`cafes` 加 `lat NUMERIC(9, 6)`、`lng NUMERIC(9, 6)`，可為 NULL（demo 的座標在 seed 之後才補上），由 `db/checks` 確保初始化完成後沒有 NULL。

### D2. real 保留座標
`CafeRow` 的 `lat`、`lng` 寫入資料庫，註解與 import-real-cafes D4 的「not stored」一併更新。以地址找不到行政區、用座標補上位置的 42 家，座標仍是自己的座標。座標屬於 Google Places 內容，和店名一樣只存在本機 real volume。

### D3. demo 產生座標
- 新增 init 腳本 `07_demo_locations.sh`，只在 `DATASET=demo` 執行，排在 `06_open_data.sh` 之後（需要站點座標）。
- 每家店取同行政區的一個 YouBike 站當錨點，再加上 0～250 公尺的偏移；錨點與偏移都由 `md5(place_id)` 決定，不呼叫 `random()`。理由：`02_seed.sql` 共用 `setseed` 的隨機序列，改動它會讓所有模擬資料與評估答案改變。
- 用 YouBike 站當錨點，店家自然落在有人活動的街區，距離分布接近真實（大多數店離捷運站幾百公尺，內湖區等稀疏區較遠）。
- CI 與測試資料庫跑同一支腳本。

### D4. 距離 view
```sql
v_cafe_transit (cafe_id, nearest_mrt, mrt_distance_m, youbike_within_300m)
```
- 直線距離用 haversine，寫成 `IMMUTABLE` 的 SQL 函式 `distance_m(lat1, lng1, lat2, lng2)`，view 與檢查共用；模型不直接使用函式：不寫進知識文件，並加入 SQL 防護的封鎖函式（view 內部呼叫時需要查詢者的 EXECUTE 權限，不能用 REVOKE 擋）。
- 一般 view，不用 materialized view：real 匯入在 init 之後執行，materialized view 需要額外的 refresh 步驟。雙北規模（711 家 × 3,398 站）以經緯度方框先篩選再算距離，目標是整個 view 在 1 秒內查完（statement timeout 5 秒）。實作時量測，超過時改用 materialized view 並在匯入後 refresh。
- 300 公尺固定寫在 view：營運最常問「附近有沒有 YouBike」，固定一個門檻比讓模型自己算距離穩定。其他門檻的 YouBike 問題不在本 change 範圍。

### D5. 讓模型會用
- 知識文件 schema 加 `cafes.lat`、`cafes.lng` 與 `v_cafe_transit`。
- 名詞：「捷運站附近／步行 5 分鐘」= `mrt_distance_m <= 400`（步行約 80 公尺／分鐘）；「附近有 YouBike」= `youbike_within_300m > 0`。說明距離是直線距離。
- `cafes` 說明寫明：距離問題用 `v_cafe_transit`，不要用 `lat`、`lng` 自己算。
- 範例已達 15 份上限，不新增；`STATIC_KNOWLEDGE` 同步。
- golden set 新增 2 題（含 1 題 hard），static 與 rag 各跑 2 次，記入 `RESULTS.md`，並記錄檢索是否取到 `v_cafe_transit`（`import-transit-open-data` 發現交通文件容易擠掉其他文件）。

### D6. 檢查
`db/checks` 新增：每家店都有座標；座標在雙北範圍（緯度 24.6～25.4、經度 121.2～122.1）；demo 每家店的最近捷運站距離都小於 5 公里（錨點在同區，超過代表產生方式有誤）。

## Risks / Trade-offs

- [demo 座標是產生的] → README 與知識文件不宣稱 demo 距離是真實的；只用來展示與評估
- [直線距離不等於步行距離] → 名詞定義寫明「直線距離」，步行時間只是換算
- [view 即時計算可能變慢] → D4 量測，必要時改 materialized view
- [新欄位讓模型自己寫距離公式] → 知識文件指示改用 view；評估中檢查產生的 SQL
- [`lat`、`lng` 加入 `cafes` 讓 static prompt 變長] → 評估記錄 token 變化
