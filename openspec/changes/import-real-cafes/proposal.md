## Why

模擬資料能保證評估可重現、不洩漏個資，但 Demo 時店名與地址都是「示範咖啡」，真實感不足。咖啡店本身是公開的店家資訊，可以在不碰任何使用者資料的前提下匯入真實店家，讓 Demo 更貼近 Find Coffee 的實際營運情境，同時展示「同一套系統可直接套用在真實資料結構上」。

## What Changes

- 新增匯入腳本：從 Find Coffee 匯出檔讀入店家，只取 `cafes`（與 `cafe_nomad_cache`）的公開欄位，由地址解析 `city`、`district`
- 新增資料集模式 `DATASET=demo|real`（預設 `demo`）：`real` 使用另一個資料庫 volume，模擬的行為資料（搜尋、瀏覽、收藏）以真實店家 id 重新產生
- 匯入檔與匯入後的資料只存在本機或 EC2，不進 repo
- README：說明兩種模式、資料來源授權與限制

### Non-goals

- 匯入任何真實會員或行為資料（搜尋、瀏覽、收藏、LINE 識別碼）
- 讓評估（golden set、CI）使用真實資料

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

- `demo-dataset`: 新增真實店家資料集模式；評估與 CI 固定使用模擬資料。

## Impact

- 新增：`db/import/` 腳本、compose 的資料集切換、README 章節
- 授權：Google Places 來源的資料受條款限制，不可散布，只能保留在私人環境；Cafe Nomad 資料需先確認授權
- 依賴 ticket：`eval-golden-set`（評估先固定在模擬資料）、`deploy-public-demo`（部署後再決定線上是否使用真實店家）

## 匯出檔現況（2026-11-08 檢查）

本機匯出檔（pgAdmin CSV，有標頭，空值寫成字串 `NULL`）不進 repo，只記錄檢查結果：

- `cafes`（店家主表）：812 家、27 欄，格式正常。
  - 地址同時有「臺北市」與「台北市」，匯入時統一寫法；部分英文地址無法解析行政區，改用經緯度對行政區界判斷。
  - `has_socket`、`limited_time` 約一半為 NULL，`has_pet`、`pet_friendly` 幾乎全為 NULL；真實資料比示範資料稀疏，評估結果不可直接比較。
  - `reviews`（Google 評論原文）、`photo_reference`、`photo_s3_url` 依 Google 條款不匯入；`view_count` 全為 0。
- `cafe_cafeattributevote`（屬性投票）：902 筆、7 欄，`cafe_id` 全部對得到 `cafes`。
  - 屬性 socket、limited_time、quiet、cheap、pet_friendly、has_pet；值 yes/maybe/no/unknown。
  - 來源 google 650、cafenomad 116、user 136；user 來源帶 `user_id`，屬於真實使用者行為，只匯入不含 `user_id` 的彙總。
- `cafe_nomad_cache`（Cafe Nomad 社群資料）：1,661 筆、21 欄，格式正常。
  - 有 wifi、seat、quiet、tasty、cheap、music 評分與捷運站 `mrt`（約 1/3 有值）。
  - 沒有對應 `cafes` 的 id，需以店名＋座標比對；授權需先確認。
