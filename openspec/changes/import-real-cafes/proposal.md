## Why

模擬資料能保證評估可重現、不洩漏個資，但 Demo 時店名與地址都是「示範咖啡」，真實感不足。咖啡店本身是公開的店家資訊，可以在不碰任何使用者資料的前提下匯入真實店家，讓 Demo 更貼近 Find Coffee 的實際營運情境，同時展示「同一套系統可直接套用在真實資料結構上」。

## What Changes

- 新增資料集模式 `DATASET=demo|real`（預設 `demo`），兩種模式使用各自的資料庫 volume
- 新增一次性匯入服務 `cafe-import`：從本機匯出檔（repo 外的目錄，唯讀掛載）讀入店家、屬性投票與 Cafe Nomad 資料，只取公開欄位，由地址解析 `city`、`district`；`demo` 模式直接略過
- `real` 模式只匯入台北市、新北市的店家（含以經緯度補上位置的），與 demo 及知識文件的城市範圍一致
- `real` 模式的會員、搜尋、瀏覽、收藏一律以模擬方式依真實店家產生
- 評估遇到非 demo 資料庫時報錯停止，CI 固定使用 demo
- README：兩種模式、資料來源授權與限制

### Non-goals

- 匯入任何真實會員或行為資料（會員、搜尋、瀏覽、收藏、使用者投票、LINE 識別碼），包括它們的彙總數字（`favorite_count`、`view_count`）
- 讓評估（golden set、CI）使用真實資料
- 經緯度欄位與距離計算（留給 `import-open-data` 第二階段）
- 公開部署真實店家資料（`deploy-public-demo` 使用 demo）

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

- `demo-dataset`: 新增真實店家資料集模式；評估與 CI 固定使用模擬資料。

## Impact

- 新增：`backend/app/real_cafes.py`（清理與比對）、`backend/scripts/import_real_cafes.py`、`backend/app/real_behavior.sql`、compose 的 `cafe-import` 服務與資料集切換、README 章節
- 修改：`cafes.pet_friendly`、`has_pet` 改為可為 NULL（真實資料多數未知）；知識文件 `schema.yaml` 同步說明
- 既有 demo volume 名稱改變，需要 `docker compose down -v` 重建一次
- 授權：Google Places 來源的欄位只能保留在私人環境；Cafe Nomad 查不到正式授權條款，只在本機使用並標示來源
- 依賴 ticket：`eval-golden-set`（評估固定在模擬資料）、`rag-knowledge-base`（schema 知識文件）

## 匯出檔現況（2026-11-10 檢查）

本機匯出檔（pgAdmin CSV，有標頭，空值寫成字串 `NULL`）不進 repo，只記錄檢查結果：

- `cafes`（店家主表）：812 家、27 欄。
  - 地址可解析城市與行政區的有 768 家（比對全台 22 縣市）：臺北市 418、新北市 258、臺中市 58、桃園市 26、其他 8 縣市各 1；44 家無法解析（中文地址缺城市或格式不同），其中 42 家以經緯度補上。
  - 只匯入台北市、新北市（D12）：711 家。
  - 地址同時有「臺北市」與「台北市」，統一成 demo 的「台北市」寫法。
  - 經緯度、評分全部有值；`has_socket`、`limited_time` 約一半為 NULL，`has_pet`、`pet_friendly` 幾乎全為 NULL。
  - `reviews`、`photo_reference`、`photo_s3_url`、`ai_summary`（由評論產生，174 家有值）依 Google 條款不匯入；`favorite_count`（34 家大於 0）是真實使用者的收藏彙總，不匯入；`view_count` 全為 0。
- `cafe_cafeattributevote`（屬性投票）：902 筆，`cafe_id` 全部對得到 `cafes`。
  - 來源 google 650、cafenomad 116、user 136；user 來源全部帶 `user_id`，屬於真實使用者行為，不匯入。
- `cafe_nomad_cache`（Cafe Nomad 社群資料）：1,661 筆，全部是台北（`city = taipei`），沒有 `cafes` 的 id，需以座標與店名比對。
