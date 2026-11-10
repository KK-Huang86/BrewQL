## Context

動機見 proposal.md。此時 demo 資料集（`db/init/02_seed.sql`）已有完整的資料故事與 26 題評估基準，RAG 知識文件描述的是同一套 schema。真實匯出檔放在 repo 外的本機目錄。

## Goals / Non-Goals

**Goals:** 一個環境變數切換 demo／real；real 模式只有公開店家資訊，其餘全是模擬；demo 資料與評估結果完全不變。

**Non-Goals:** 定期同步 Find Coffee；經緯度與距離；公開部署 real 模式。

## Decisions

### D1. 兩種模式各用一個 volume
`DATASET=demo|real`（預設 `demo`），compose 的資料庫 volume 名稱帶上模式（`genbi_pgdata_demo`、`genbi_pgdata_real`）。切換模式不會覆蓋另一邊的資料，也不會把真實店家混進 demo。代價是既有 volume 改名，需要重建一次。

### D2. 匯入檔留在 repo 外
匯出檔目錄由 `REAL_DATA_DIR` 指定（絕對路徑），唯讀掛進 `cafe-import` 容器；repo 內沒有任何真實資料。另在 `.gitignore` 加上 `db/import/`，防止有人把檔案複製進 repo。

### D3. 用 Python 一次性服務匯入，沿用 knowledge-import 的模式
`cafe-import` 在 db 健康後、`knowledge-import` 與 backend 之前執行：
- `DATASET=demo`：直接 exit 0。
- `DATASET=real` 且 `cafes` 已有資料：exit 0（只匯入空資料庫；匯出檔更新時重建 real volume）。
- 否則：讀檔、清理、在一個交易內寫入店家、投票、Cafe Nomad，再執行 `backend/app/real_behavior.sql` 產生模擬行為；任何一步失敗就 rollback，exit 1，backend 不啟動。

清理與比對寫成純函式（`app/real_cafes.py`），用假資料單元測試；不在 SQL 裡做字串解析，邊界情況比較好測。寫入使用資料庫擁有者帳號，只出現在 `cafe-import` 容器，backend 仍只用 `genbi_reader`。

### D4. 只匯入公開欄位
匯入：`place_id`、`name`、`address`、`city`、`district`（解析）、`rating`、`user_ratings_total`、`has_socket`、`limited_time`、`pet_friendly`、`has_pet`、`created_at`。

不匯入：`phone`、`website`、`opening_hours`、`google_maps`、`reviews`、照片欄位、`ai_summary`、`lat`／`lng`（schema 沒有，只用於比對與補行政區）、`favorite_count`、`view_count`（由模擬資料重算，維持「計數等於明細列數」）。

欄位用白名單挑選：新的匯出欄位預設不匯入。

### D5. 地址解析與補行政區
- 規則：`(城市)(1~4 字 + 區／鄉／鎮／市)`；「臺」統一成「台」（demo 與知識文件的寫法）。
- 無法解析時，用經緯度找最近的已解析店家，距離 1 公里內就沿用它的城市與行政區；否則 `city`、`district` 為 NULL。
- 匯入報告列出解析、補上、仍為 NULL 的家數。

### D6. 屬性投票只匯入 google 與 cafenomad 來源
`source = user` 的 136 筆是真實使用者行為，整筆不匯入（不是只去掉 `user_id`）。google 650、cafenomad 116 筆照原樣匯入，`cafe_id` 對到新的店家 id。

### D7. Cafe Nomad 以座標＋店名比對
每筆 Cafe Nomad 找 50 公尺內的店家，正規化店名（去空白、全半形、括號內分店名）後互相包含才算同一家；一家店只對一筆，取距離最近的。對不到的丟棄（`cafe_nomad_cache.cafe_id` 必填），匯入報告列出比對成功與丟棄的筆數。評分 0 視為未評分（NULL），與 demo 一致。

### D8. 寵物欄位改為可為 NULL
真實資料的 `pet_friendly`、`has_pet` 幾乎全是 NULL，轉成 FALSE 會把「不知道」說成「不行」。schema 拿掉 `NOT NULL`；demo 仍全部有值，資料不變。`schema.yaml` 補上「NULL 表示未知」。

### D9. real 模式的行為資料另寫一份 SQL
`backend/app/real_behavior.sql`（跟著 backend image 打包，匯入容器才讀得到）參考 demo seed 的做法（固定 `setseed`、會員、搜尋、瀏覽依評分與評論數加權、收藏由瀏覽轉換、計數等於明細），但各行政區的搜尋比例依店家數計算，不重現 demo 特有的資料故事（例如內湖區落差）。不與 demo seed 共用：共用需要重構 `02_seed.sql`，風險是改到 demo 資料、評估基準失效。

### D10. 評估只在 demo 上執行
評估開始前檢查 `cafes.place_id` 全部以 `demo-` 開頭，否則報錯停止，在任何付費呼叫之前。CI 不設定 `DATASET`，使用預設 demo。

### D11. 授權與散布
Google Places 來源的欄位（店名、地址、評分、評論數、`place_id`）只保留在本機的 real volume。Cafe Nomad 查不到正式授權條款，只在本機使用，README 標示來源。公開部署一律使用 demo。

## Risks / Trade-offs

- [店名比對誤配] → 50 公尺＋店名互相包含；匯入報告列出筆數，人工抽查
- [real 模式資料稀疏、分布與 demo 不同] → 不用 real 做評估；README 說明 real 模式只供展示
- [volume 改名，既有 demo 資料需重建] → README 與 PR 說明寫明 `docker compose down -v`
- [匯入使用擁有者帳號] → 只在一次性容器中，backend 與 API 不接觸；只寫入空資料庫
