## 1. 前置確認

- [x] 1.1 記錄資料來源授權（Google Places 條款、Cafe Nomad 查無正式條款）與匯入、不匯入的欄位；驗證：design D4、D11 與 README 草稿一致
  - 結果：欄位白名單記於 D4，授權記於 D11。Google Maps Platform 條款只允許長期保存 `place_id`，其他 Places 內容（店名、地址、評分、評論數）不得散布，因此只放在本機 real volume，公開部署用 demo；這些資料本來就存在 Find Coffee 的資料庫，本 change 不新增對 Google 的呼叫。Cafe Nomad 只找到開發者文件與第三方 App 的來源標示，查無正式資料授權條款，只在本機使用並於 README 標示來源。README 段落在 4.2 依 D4、D11 撰寫

## 2. 清理與比對（純函式）

- [x] 2.1 測試 + 實作：地址解析城市與行政區（臺→台、無法解析回傳 None）；驗證：測試由紅轉綠
  - 結果：`app/real_cafes.py` 的 `parse_address`，城市清單涵蓋全台 22 縣市，行政區必須緊接城市、1～4 字加區／鄉／鎮／市，路名（例如中山北路）不會被當成行政區。11 個測試紅轉綠（紅燈原因為模組不存在），地址皆為虛構。對真實匯出檔只算統計：812 家中 768 家解析成功（台北市 418、新北市 258、台中市 58、桃園市 26、其他 8 縣市各 1），51 個行政區名稱全部是真實行政區；44 家留給 2.2 以經緯度補
- [x] 2.2 測試 + 實作：無法解析時以 1 公里內最近的已解析店家補上；驗證：測試由紅轉綠
  - 結果：`locate` 回傳每家店的位置與報告（解析、補上、未知家數），距離用 haversine。只有地址解析成功的店家能當參考點，補上的位置不再傳給別家，避免一路跨過行政區界。3 個測試紅轉綠（紅燈原因為 `Place`、`locate` 不存在）。真實匯出檔：解析 768、補上 42、未知 2。準確度估計：對已解析的店家做留一驗證，1 公里內最近店家的行政區相同 694/727（95%），補上的 42 家約有 2 家可能落在相鄰行政區
- [x] 2.3 測試 + 實作：店家欄位白名單、NULL 字串轉換、投票排除 user 來源；驗證：測試由紅轉綠，輸出不含 `user_id`、`favorite_count`
  - 結果：`clean_cafe` 回傳 `CafeRow`（白名單欄位，新出現的匯出欄位自動忽略），`clean_votes` 回傳保留的投票與排除筆數；`NULL` 字串轉 None，寵物欄位 yes/no 轉布林、未知保持 None，其他值報錯。3 個測試紅轉綠（紅燈原因為 `CafeRow` 等不存在），驗證輸出沒有 `user_id`、`favorite_count`、`view_count`、評論與摘要。真實匯出檔：812 家全部清理成功；投票保留 766（google 650、cafenomad 116）、排除 user 136，保留的投票全部對得到店家
- [x] 2.4 測試 + 實作：Cafe Nomad 以 50 公尺＋店名比對，一家店只對一筆，評分 0 轉 NULL；驗證：測試由紅轉綠
  - 結果：`match_nomad` 回傳比對到的資料與報告（對不到、重複的筆數）。店名正規化：全形轉半形、去括號內分店名、小寫、去掉通用字（咖啡、咖啡館、coffee、cafe 等）後只留文字與數字；剩下的較短名稱須至少 2 個中文字或 3 個英文字母，且被另一名稱包含。兩輪紅轉綠：第一輪基本比對（紅燈原因為 `match_nomad` 不存在）；真實資料只對到 135 家，診斷發現 50 公尺內有店但店名不合的 267 筆中，有同一家店因「咖啡／coffee」寫法不同而漏掉，第二輪去掉通用字（紅燈 3 個；舊測試的「好咖啡」去掉通用字後只剩一字，以獨立 `test:` commit 改名）。真實匯出檔：1,661 筆中對到 147 家（台北市 108／439 家），對不到 1,511、重複 3；名稱不完全相同的 49 對抽查 25 對皆為同一家店。50～150 公尺內同名的 9 筆未納入，維持 50 公尺

## 3. 匯入與資料集模式

- [x] 3.1 schema：`pet_friendly`、`has_pet` 可為 NULL，`schema.yaml` 同步；驗證：demo 重建後評估參考 SQL 試跑（`--dry-run`）結果不變
  - 結果：`01_schema.sql` 拿掉兩欄的 `NOT NULL`（保留預設 FALSE），`schema.yaml` 與 `STATIC_KNOWLEDGE` 補「NULL 表示未知」。整合測試以擁有者帳號在 rollback 的交易內寫入 NULL，紅燈原因為 not-null constraint；另一個測試確認 demo 店家沒有 NULL。測試資料庫與 CI 新增 `TEST_OWNER_DATABASE_URL`（3.2 匯入也要用）。重建測試資料庫後：全部 660 個測試通過，評估 `--dry-run` 22 題參考 SQL 全部 ok，`db/checks` 8 個檔案全部通過
- [x] 3.2 測試 + 實作：匯入腳本在一個交易內寫入，demo 模式與已有資料時略過，失敗 rollback；驗證：整合測試由紅轉綠
  - 結果：三個切片各自紅轉綠。`prepare` 把三份匯出串成一批並產生報告，投票對不到店家時報錯；`scripts/import_real_cafes.py`：demo 略過且不讀檔、已有店家略過、找不到唯一的匯出檔或內容無效 exit 2、寫入失敗 exit 1（6 個單元測試）；`app/real_cafes_store.py` 的 `PgRealCafeStore`：一個交易內 `LOCK TABLE cafes` 後確認仍為空，寫入店家、以 `place_id` 對應新 id 後寫入投票與 Cafe Nomad，連線在第一次使用時才建立（demo 不連線）。整合測試在臨時建立的空資料庫（套用 `01_schema.sql`）驗證 id 對應與中途失敗全部 rollback；mutation：拿掉交易與 lock 後 rollback 測試失敗
- [x] 3.3 `backend/app/real_behavior.sql`：依真實店家產生模擬行為，計數等於明細；驗證：整合測試確認會員、搜尋、瀏覽、收藏皆為模擬且計數等於明細
  - 結果：路徑由 `db/seed/` 改為 `backend/app/`（匯入容器的 image 只有 backend）；驗證由 `db/checks` 改為整合測試，因為 `db/checks` 檢查的是 demo 的資料故事（例如內湖區落差），real 本來就不成立。SQL 沿用 demo seed 的會員、搜尋（考試季）、瀏覽（依評分與評論數加權）、收藏轉換與回訪，固定 `setseed`；搜尋只落在有真實店家的行政區，比例依店家數；不產生 Cafe Nomad 與投票（用真實匯入的）。在匯入交易內執行，失敗一起 rollback。整合測試紅轉綠：2,000 會員、搜尋超過 4 萬、瀏覽超過 15 萬、搜尋行政區都有店家、計數等於明細、沒有在加入前的搜尋、沒有 user 來源投票。已加入會員數改用 `width_bucket`，測試由 14.6 秒降為 4.3 秒；mutation：拿掉計數更新後測試失敗
- [x] 3.4 compose：`DATASET`、各自的 volume、`cafe-import` 服務（`REAL_DATA_DIR` 唯讀掛載）；`.gitignore` 加 `db/import/`；`.env.example` 同步；驗證：兩種模式都能啟動，`git status` 看不到匯入檔
  - 結果：demo seed 移到 `db/init/demo/02_seed.sql`，由 `db/init/02_seed.sh` 在非 real 時執行（Postgres 只執行 init 目錄第一層的檔案）；CI 改跑該腳本。compose：db 帶 `DATASET`、volume 名稱 `genbi_pgdata_${DATASET:-demo}`、新增 `cafe-import`（擁有者連線只給這個容器），backend 等它成功才啟動；db 健康檢查改走 TCP，init 期間 Postgres 只聽 socket，避免匯入在 init 完成前連線。實測：測試資料庫 demo 200 家、671 個測試與 8 個 `db/checks` 通過；`DATASET=real` 匯入報告 `cafes=812 parsed=768 filled=42 unknown=2 votes=766 member_votes_dropped=136 nomad_matched=147 nomad_unmatched=1511 nomad_duplicates=3`，資料庫 demo 店家 0、會員 2,000、搜尋 50,000、瀏覽 202,105、收藏 17,075、user 投票 0、知識文件 32；再次啟動顯示 already has cafes；不帶 `DATASET` 啟動回到 demo（200 家，新 volume `genbi_pgdata_demo`）。`db/import/` 下的檔案 `git status` 看不到。舊 volume `genbi_pgdata` 不再使用
- [ ] 3.5 測試 + 實作：評估遇到非 demo 店家時在付費呼叫前報錯停止；驗證：測試由紅轉綠

## 4. 驗證與文件

- [ ] 4.1 實際以 real 模式啟動並提問；驗證：匯入報告的筆數記入本檔，3 個問題的回答與 SQL 抽查合理
- [ ] 4.2 README：兩種模式、切換方式、資料來源與授權限制；驗證：照 README 從 demo 切到 real 再切回 demo 成功
