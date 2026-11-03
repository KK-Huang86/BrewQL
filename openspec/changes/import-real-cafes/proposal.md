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
