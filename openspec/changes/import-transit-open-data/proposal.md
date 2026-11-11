## Why

`import-open-data` 第一階段讓模型能以人口、大專校院解釋行政區差異，但營運人員常問的「交通方便的區咖啡店是否比較多」「YouBike 站多的區搜尋是否也多」仍答不了。YouBike 與捷運是雙北找咖啡店時最常用的交通方式，加入後回答的面向更完整。

原計畫第二階段直接做距離串接，但 `cafes` 目前沒有經緯度（real 匯入只用座標比對、不儲存；demo 沒有座標）。因此拆成兩個 change：本 change 先以**行政區**串接交通資料（沿用第一階段做法），下一個 change `cafe-transit-distance` 再替 `cafes` 加座標並提供距離 view。本 change 的快照保留站點經緯度，讓下一個 change 直接使用。

## What Changes

| 資料 | 來源 | 串接方式 | 可回答的問題 |
|---|---|---|---|
| YouBike 2.0 站點（台北） | 臺北市政府交通局「YouBike2.0 臺北市公共自行車即時資訊」 | `district` | 各區 YouBike 站數、車柱數與咖啡店數、搜尋量的關係 |
| YouBike 2.0 站點（新北） | 新北市政府交通局「YouBike2.0 新北市公共自行車即時資訊」 | `district` | 同上 |
| 捷運車站 | 臺北大眾捷運公司「臺北捷運車站出入口座標」（data.gov.tw/dataset/128428） | `district` | 各區捷運站數、沒有捷運站但搜尋多的區 |

- 新增資料表 `youbike_stations`、`mrt_stations`，以固定版本快照匯入，只收台北市、新北市
- 快照由 `prepare_open_data.py` 從官方下載檔裁成需要的欄位；即時欄位（可借車輛、可還空位）不收
- 捷運資料只有出入口座標，沒有行政區：以出入口平均座標為車站位置，行政區取最近 YouBike 站的行政區，並以官方車站地址抽查邊界車站
- SQL 白名單、`genbi_reader` 權限、串接檢查、知識文件（schema、名詞）加入新表
- golden set 新增跨來源交通題目，評估 rag 正確率與 token
- README 資料來源加入兩份資料

### Non-goals

- 咖啡店到車站的距離（`cafe-transit-distance`）
- YouBike 即時車輛數、借還量；捷運各站進出量
- 機場捷運、淡海／安坑輕軌（不在臺北捷運公司的出入口資料內）
- 捷運路線（資料沒有路線欄位）

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

- `open-data`: 快照加入 YouBike 站點與捷運車站。
- `sql-guardrails`: 白名單加入兩張交通表。
- `evaluation`: golden set 加入交通相關的跨來源題目。

## Impact

- 修改：`backend/app/open_data.py`、`backend/scripts/prepare_open_data.py`、`db/init/01_schema.sql`、`db/init/06_open_data.sh`、`db/checks/09_open_data_join.sql`、SQL 白名單、`schema_context.py`、知識文件、golden set、README
- 新增：`db/init/open_data/youbike_stations.csv`、`db/init/open_data/mrt_stations.csv`
- 本機資料庫需重建（`down -v`）才會有新表
- 授權：政府資料開放授權條款第 1 版
- 依賴：`import-open-data`（PR #38）

## 來源檔現況（2026-11-11 檢查）

- 台北 YouBike：JSON 1,824 站（停用 21），欄位 `sno, sna, sarea, ar, Quantity, latitude, longitude, act` 與即時欄位。`sarea` 有 12 個行政區加上「臺大公館校區」（65 站）。
- 新北 YouBike：JSON 1,622 站（停用 27），欄位 `sno, sna, scity, sarea, ar, tot_quantity, lat, lng, act` 與即時欄位，數值為字串；29 區全有站。
- 捷運出入口：CSV（Big5）390 列，欄位 `項次, 出入口名稱, 出入口編號, 經度, 緯度, 是否為無障礙用`，整理後約 119 站（含環狀線）。名稱寫法不一，例如「頂埔站出口1」與「台北車站M5…」。
