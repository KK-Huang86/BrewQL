## Context

動機見 proposal.md。`import-open-data` 已建立快照流程（`app/open_data.py` 純函式裁切 → `prepare_open_data.py` 寫檔 → `06_open_data.sh` 載入）、串接檢查（`db/checks/09_open_data_join.sql`）與知識文件寫法（以 `district` 串接）。本 change 沿用同一套流程。

## Goals / Non-Goals

**Goals:** YouBike 與捷運以行政區串到既有資料；快照可重現並保留座標供下一個 change 使用；新表受 SQL 防護；評估量化交通題目正確率。

**Non-Goals:** 店家距離、即時資料、PostGIS、捷運路線與運量。

## Decisions

### D1. 資料表
```sql
youbike_stations (station_no, name, city, district, docks, lat, lng, as_of)  -- PRIMARY KEY (station_no)
mrt_stations     (name, city, district, exit_count, lat, lng, as_of)         -- PRIMARY KEY (name)
```
- `station_no` 為官方 `sno`；`name` 去掉「YouBike2.0_」前綴；`docks` 為車柱數（台北 `Quantity`、新北 `tot_quantity`）。
- 只收營運中的站（`act = '1'`），停用站對「這區有多少站」沒有意義。
- `as_of` 為下載日：即時資料沒有版本號，快照時間就是資料時間。
- `lat`、`lng` 為 `NUMERIC(9, 6)`；本 change 不使用，供 `cafe-transit-distance` 計算距離。

### D2. 行政區正規化
- 城市寫法統一為「台」（沿用 `demo_spelling`），只收雙北。
- 台北的「臺大公館校區」不是行政區，對應到大安區（校區主體位於大安區）。
- 其他 `sarea` 必須在 `district_population` 的 41 區內，否則裁切腳本報錯（D5 的檢查會再擋一次）。

### D3. 捷運車站：從出入口推出
- 站名：出入口名稱去掉結尾的出入口編號（例如 `1`、`M5`）、「出口」與「站」，例如「頂埔站出口1」→「頂埔」。例外是「台北車站M5」：官方站名就是「台北車站」，去掉「站」會變成「台北車」，因此保留。規則寫成純函式，測試列出這兩種情況。
- 位置：同站出入口經緯度平均。
- 行政區：取離車站位置最近的營運中 YouBike 站的城市與行政區。理由是不必引入行政區界圖資。
- 已知風險：邊界車站可能判錯。原計畫抽查 19 站，實作時找到臺北捷運官網車站頁使用的 API（`web.metro.taipei/apis/metrostationapi/stationdetail`），因此改成 119 站全部和官方地址比對：7 站判錯（公館、南京復興、台電大樓、國父紀念館、後山埤、忠孝新生、雙連），以程式中的明確對照表 `MRT_DISTRICT_FIXES` 修正，並在測試中列出。官網 API 不是公開資料集（授權不明），只用來人工核對，不作為快照來源，也不放進 repo。

### D4. 載入、權限、檢查
- `06_open_data.sh` 再 `\copy` 兩個快照並 GRANT SELECT 給 `genbi_reader`。
- `09_open_data_join.sql` 的行政區檢查加入 `youbike_stations` 與 `mrt_stations`。

### D5. 讓模型會用
- 知識文件 schema 加兩張表，寫明以 `district` 串接、`docks` 意義、捷運站只含臺北捷運公司路網。
- 名詞：「每萬人 YouBike 站數」不新增（已有每萬人寫法可套用），新增「交通便利度」名詞說明可用站數或車柱數衡量，避免模型自創指標。
- 範例：`examples.yaml` 已有 15 題，達 `rag-knowledge-base` 的上限，不新增範例。
- `STATIC_KNOWLEDGE`（`schema_context.py`）同步加入兩張表與名詞。評估後只為了 rag 檢索調整 yaml 文件的文字（拿掉城市值等通用字眼，見 RESULTS.md），`STATIC_KNOWLEDGE` 維持 static 評估時的文字，因此兩者內容相同、措辭刻意不同。
- golden set 新增 2 題（含 1 題 hard）；static 與 rag 各跑 2 次，記入 `RESULTS.md`。原本想出「沒有捷運站的行政區中搜尋最多的區」，但 demo 的店家與搜尋只在 10 個行政區，全部有捷運站，答案會是空的；改成「捷運站最多的 3 區各有幾家店」（北投區 0 家，考 LEFT JOIN 與補 0）與「YouBike 車柱數前 3 區中，每個車柱搜尋次數最高的區」（考先各自彙總再串接）。

## Risks / Trade-offs

- [快照是某一天的即時資料] → `as_of` 與 README 標明日期；站點數量變動緩慢，對行政區層級比較影響小
- [捷運行政區用最近 YouBike 推估] → D3 抽查與對照表；不準時影響的是站數，而非咖啡店資料
- [新表讓 static prompt 變長] → 評估記錄 token 變化；rag 只取用到的表
- [官方 API 網址或欄位改變] → 快照已在 repo，Demo 不受影響；重產時腳本以缺欄位報錯
