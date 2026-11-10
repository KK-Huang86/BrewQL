## Why

目前的分析只看得到 Find Coffee 自己的資料（店家、會員、搜尋），能回答「哪裡搜尋多、哪裡店少」，卻回答不了「為什麼」。加入政府公開資料當補充，可以讓營運問題連到外部背景，例如人口多但咖啡店少的區、學校多的區搜尋是否也多。

考慮過把整套資料換成公開資料（例如只做台北自行車或人口分析），但那會讓產品變成另一個題目，評估集、圖表故事與 Find Coffee 的定位都要重來。因此選擇第三條路：**保留 Find Coffee，再加入公開資料，以行政區（或座標）串接**。

## What Changes

本 change 是公開資料的**第一階段：行政區串接**。第二階段（YouBike、捷運，以距離串接）另開 change。

| 資料 | 來源 | 串接方式 | 可回答的問題 |
|---|---|---|---|
| 行政區人口與面積 | 內政部戶政司「各鄉鎮市區人口密度」114 年底（data.gov.tw/dataset/8410） | `district` | 每萬人有幾家咖啡店、人口多但店少的區 |
| 大專校院 | 教育部「全國大學校院名錄」108 學年度（data.gov.tw/dataset/33207） | `district` | 學校多的區搜尋是否也多 |

- 新增資料表 `district_population`、`universities`，以固定版本快照匯入（唯讀、可重現），只收台北市、新北市
- 快照由腳本從官方下載檔裁成需要的欄位後放進 repo；`demo` 與 `real` 資料集都會載入
- SQL 白名單、`genbi_reader` 權限、知識文件（schema、名詞「每萬人咖啡店數」、範例）加入新表
- golden set 新增跨資料來源題目，評估 rag 正確率與 token
- README 標示資料來源與授權

### Non-goals

- 取代 Find Coffee 資料或改變既有評估題目
- 即時串接公開資料 API（只匯入快照，避免外部服務影響 Demo 與評估）
- 距離串接（第二階段）、行政區界圖資

## Capabilities

### New Capabilities

- `open-data`: 政府公開資料快照（行政區人口、大專校院）的匯入、串接與來源標示。

### Modified Capabilities

- `sql-guardrails`: 白名單加入公開資料表。
- `evaluation`: golden set 加入跨資料來源題目。

## Impact

- 新增：`backend/scripts/prepare_open_data.py`（官方檔 → 快照）、`db/init/open_data/*.csv`（快照）、`db/init/06_open_data.sh`、知識文件與 golden set 題目、README 資料來源章節
- 修改：SQL 白名單、`genbi_reader` 權限、`STATIC_KNOWLEDGE`
- 本機資料庫需重建（`down -v`）才會有新表
- 授權：政府資料開放授權條款第 1 版，可散布，需標示來源
- 依賴 ticket：`district-gap-bar-chart`（行政區長條圖直接重用）、`rag-knowledge-base`、`import-real-cafes`

## 來源檔現況（2026-11-10 檢查）

- 人口：371 列（全國鄉鎮市區），欄位 `statistic_yyy, site_id, people_total, area, population_density`，第 2 列是中文欄名；`site_id` 為「新北市板橋區」這種縣市加行政區的字串，雙北 41 區（台北 12、新北 29）。
- 大專校院：160 所，欄位含學校代碼、公私立、體制、學校名稱、縣市別、第三級行政區、地址，另有校長職稱與姓名、電話傳真；雙北 49 所（台北 26、新北 23）。資料為 108 學年度，官方之後沒有更新，少數學校可能已合併或改名。
