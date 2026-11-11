## 1. 店家座標

- [x] 1.1 `cafes` 新增 `lat`、`lng`；測試 + 實作：real 匯入寫入座標（含以座標補上位置的店家）；驗證：測試由紅轉綠，重建 real 後 711 家都有座標
  - 結果：整合測試紅轉綠（紅燈 `column "lat" does not exist`），驗證兩家店都存入匯出檔座標，含以鄰店補上行政區的 p2。`real_cafes_store` 的 INSERT 多了 `lat`、`lng`，`CafeRow` 註解改為會儲存。全部 730 個測試通過。重建 real 的 711 家驗證併入 4.1，避免多次重建 real volume
- [x] 1.2 `07_demo_locations.sh`：demo 店家依 D3 產生座標，CI 與測試資料庫一併執行；驗證：整合測試確認 200 家都有座標且在同區 YouBike 錨點 250 公尺內，重建兩次座標相同，既有 `db/checks` 與 `--dry-run` 答案不變
  - 結果：3 個整合測試紅轉綠（紅燈 `(200, 0, 0) == (200, 200, 200)`）：200 家都有座標、都在同區某個 YouBike 站 251 公尺內（含 6 位小數的進位誤差）、大安區 40 家分散在至少 30 個位置。錨點、方位、距離取自 `md5(place_id)` 的三段 28 位元，不使用 `random()`。CI workflow 加入 `07_demo_locations.sh`；測試資料庫掛載整個 init 目錄，不需修改。重建兩次座標的 md5 相同。golden set 27 題參考答案：除了依建庫時間產生的 q16（每月搜尋次數）之外全部不變；q16 在沒有 `07` 的兩次重建之間也會變（搜尋時間以 `now()` 為基準），與座標無關。`db/checks` 全部通過，全部 733 個測試通過

## 2. 距離 view 與防護

- [x] 2.1 `distance_m` 函式與 `v_cafe_transit`，授權 `genbi_reader`；驗證：整合測試以已知座標驗證距離（誤差 < 1%）與 300 公尺內站數，量測 real 模式整個 view 的查詢時間
  - 結果：4 個整合測試紅轉綠（紅燈 `relation "v_cafe_transit" does not exist`）。已知距離在東部外海（25.30 N 122.05 E，遠離所有真實站點）以 owner 交易建立、測完一定 rollback：500 公尺的測試站為最近站且誤差 < 1%，100、250 公尺的 YouBike 計入、350 公尺不計入；SQL 的 `distance_m` 與 Python 的 haversine 相對誤差 < 1e-6（台北車站到板橋）；demo 200 家都有一列。YouBike 先以經緯度方框篩選再算距離。效能：在交易中加入 511 家假店家湊到 real 的 711 家，`EXPLAIN ANALYZE` 整個 view 386 ms（目標 1 秒、timeout 5 秒），維持一般 view，不需要 materialized view。`genbi_reader` 授權寫在 `03_readonly_role.sh`，和其他 view 相同
- [x] 2.2 測試 + 實作：SQL 白名單加入 `v_cafe_transit`；驗證：測試由紅轉綠
  - 結果：測試紅轉綠（紅燈 `不允許的資料表：v_cafe_transit`）。知識文件測試要求白名單每張表都有一份 schema 文件，因此 `schema-v_cafe_transit` 與 `cafes.lat`、`lng` 的說明（含「距離問題用 view，不要自己計算」）在這裡一起加入 `schema.yaml` 與 `STATIC_KNOWLEDGE`（屬於 3.1）。`distance_m` 函式不在白名單與知識文件中
- [ ] 2.3 `db/checks` 新增座標檢查（D6）；驗證：demo 通過，mutation 把一家店移到台中時失敗

## 3. 模型與評估

- [ ] 3.1 知識文件與 `STATIC_KNOWLEDGE`：`cafes` 座標、`v_cafe_transit`、名詞「捷運站附近／步行 5 分鐘」「附近有 YouBike」；驗證：知識文件測試通過、名詞中的 SQL 以唯讀角色可執行
- [ ] 3.2 golden set 新增 2 題距離題目；驗證：`--dry-run` 全部 ok
- [ ] 3.3 static 與 rag 各跑 2 次評估；驗證：結果、token 變化與檢索情況記入 `RESULTS.md`

## 4. 文件

- [ ] 4.1 README：座標來源（real 為匯出檔、demo 為產生）、距離是直線距離；real 模式實際提問 1 題距離問題；驗證：照 README 重建 demo 與 real 都有 view
