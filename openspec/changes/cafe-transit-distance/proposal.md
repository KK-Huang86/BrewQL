## Why

`import-transit-open-data` 以行政區串接 YouBike 與捷運，只能回答「捷運站多的區有幾家店」這種區層級的問題。營運人員更常問的是店家層級的問題，例如「離捷運站 5 分鐘內的不限時咖啡店」「哪些店附近沒有 YouBike」，這需要店家到站點的距離。

站點的經緯度已經在快照裡，缺的是店家這一邊：`cafes` 沒有經緯度（real 匯入只拿座標比對、不儲存；demo 店家本來就沒有座標）。

## What Changes

- `cafes` 新增 `lat`、`lng`
  - real：匯入時保留匯出檔的經緯度（目前讀了但丟掉）
  - demo：初始化時依店家所在行政區產生固定的座標（不改變既有的隨機序列，其他 demo 資料與評估答案不變）
- 新增 view `v_cafe_transit`：每家店最近的捷運站、直線距離（公尺），以及 300 公尺內的 YouBike 站數。模型直接查 view，不自己寫距離公式
- SQL 白名單、`genbi_reader` 權限、知識文件（schema、名詞「步行 5 分鐘」「捷運站附近」）加入新欄位與 view
- `db/checks` 新增檢查：每家店都有座標、座標落在雙北範圍內、demo 店家離最近捷運站都在合理距離內
- golden set 新增距離題目，評估 static 與 rag

### Non-goals

- 步行路徑距離或時間（只算直線距離，以名詞定義換算）
- PostGIS、空間索引（雙北規模用一般 SQL 計算即可）
- 店家到捷運出入口的距離（快照只有車站平均座標）
- 修改 Find Coffee 本身或對外公開 real 模式的座標

## Capabilities

### New Capabilities

- `transit-distance`: 店家到捷運站、YouBike 站的距離 view 與其定義。

### Modified Capabilities

- `demo-dataset`: `cafes` 有經緯度；real 匯入保留座標，demo 產生固定座標。
- `sql-guardrails`: 白名單加入 `v_cafe_transit`。
- `evaluation`: golden set 加入距離題目。

## Impact

- 修改：`db/init/01_schema.sql`（欄位與 view）、`backend/app/real_cafes.py` 與 `real_cafes_store.py`（保留座標）、SQL 白名單、`schema_context.py`、知識文件、golden set、README
- 新增：demo 座標產生腳本（init 階段、在公開資料載入之後執行）、`db/checks` 座標檢查
- 本機資料庫需重建（demo 與 real 都要 `down -v`）
- 授權：real 的座標來自 Google Places（經 Find Coffee），與店名相同只留在本機 real volume，不散布
- 依賴：`import-transit-open-data`（PR #40）
