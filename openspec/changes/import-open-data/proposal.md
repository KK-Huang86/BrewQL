## Why

目前的分析只看得到 Find Coffee 自己的資料（店家、會員、搜尋），能回答「哪裡搜尋多、哪裡店少」，卻回答不了「為什麼」。加入政府公開資料當補充，可以讓營運問題連到外部背景，例如人口多但咖啡店少的區、交通方便的工作友善咖啡店。

考慮過把整套資料換成公開資料（例如只做台北自行車或人口分析），但那會讓產品變成另一個題目，評估集、圖表故事與 Find Coffee 的定位都要重來。因此選擇第三條路：**保留 Find Coffee，再加入公開資料，以行政區（或座標）串接**。

> 這份 proposal 目前只記錄考量，尚未排入實作；capability 與 spec delta 待排程時再補。

## What Changes

- 新增公開資料表（唯讀，匯入腳本產生，固定版本快照，評估可重現）：
  - **行政區人口**：`city`、`district`、人口數（內政部戶政司或各縣市民政局開放資料）
  - **YouBike 站點**：站名、`city`、`district`、經緯度、車柱數（台北市、新北市 YouBike 2.0 開放資料）
- 以 `city` + `district` 與 `cafes` 串接；YouBike 另可用經緯度算「咖啡店附近 N 公尺內的站數」
- schema context 加入新表說明與名詞，例如「每萬人咖啡店數」、「交通方便」的定義
- SQL 防護白名單與 `genbi_reader` 權限加入新表
- golden set 新增跨資料來源的題目，例如：
  - 每萬人有幾家咖啡店，依行政區排序
  - 人口多但咖啡店少的區
  - 每家咖啡店附近有幾個 YouBike 站
  - 交通方便的工作友善咖啡店

### Non-goals

- 取代 Find Coffee 資料或改變既有評估題目
- 即時串接公開資料 API（只匯入快照，避免外部服務影響 Demo 與評估）

## 與 RAG 的關係

加入更多資料**不需要**先做 RAG：

- **查詢速度**取決於 SQL 與索引（資料量在數萬筆內，Postgres 直接處理）；跨表 join 需要的是 `district` 索引，不是 RAG。
- **RAG（`rag-knowledge-base`）解決的是 schema context 太長**：資料表、名詞、範例變多後，每題都把全部說明送給模型會增加 token 成本（ticket 6 後已從約 1,108 增加到約 1,690 input tokens）並可能降低正確率。RAG 只檢索與問題相關的表與範例。
- 決策方式：加入公開資料後量測 golden set 的 token 與正確率；若 input tokens 或錯誤明顯增加，再優先做 RAG。

## Impact

- 新增：`db/import/` 匯入腳本與快照檔、`db/init` 的新表與權限、schema context、golden set 題目、README 資料來源與授權說明
- 修改：SQL 防護白名單
- 授權：政府資料開放授權條款（OGDL）可散布，需在 README 標示來源
- 依賴 ticket：`district-gap-bar-chart`（行政區長條圖可直接重用）；排程待定，預計在 `view-favorite-insights` 之後評估
