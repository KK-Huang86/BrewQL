## MODIFIED Requirements

### Requirement: 咖啡店資料
資料庫 SHALL 包含沿用 Find Coffee 結構的 `cafes`（含 `city`、`district`、`rating`、`limited_time`、`has_socket`、`lat`、`lng` 等），約 200 家示範咖啡店，分布於台北市與新北市多個行政區，並使用固定亂數種子。示範店家的座標 SHALL 在初始化時依所在行政區產生，落在同行政區的 YouBike 站附近；產生方式 MUST NOT 使用共用的亂數序列，其他模擬資料 SHALL 與加入座標前相同。

#### Scenario: 分布
- **WHEN** 依城市與行政區統計 `cafes`
- **THEN** 台北市與新北市都有資料，至少 8 個行政區

#### Scenario: 可重現
- **WHEN** 刪除 volume 後重建
- **THEN** 各行政區咖啡店數量與每家店的座標都與重建前相同

#### Scenario: 座標不影響其他模擬資料
- **WHEN** 加入座標後重建 demo 資料庫並執行 golden set `--dry-run`
- **THEN** 每題參考答案與加入座標前相同

### Requirement: 真實店家資料集模式
系統 SHALL 支援 `DATASET=real` 模式，從 repo 外的本機匯出檔匯入真實店家的公開欄位與經緯度、google 與 cafenomad 來源的屬性投票、以及比對得到店家的 Cafe Nomad 資料。欄位 SHALL 以白名單挑選。匯入 MUST NOT 包含任何會員或行為資料及其彙總（會員、搜尋、瀏覽、收藏、使用者投票、`favorite_count`、`view_count`）；行為資料 SHALL 以模擬方式依真實店家產生。只有城市為台北市或新北市的店家 SHALL 被匯入（位置可由經緯度補上）；其他縣市與位置未知的店家，連同它們的投票，MUST NOT 被匯入。預設模式 MUST 為 `demo`，兩種模式 SHALL 使用各自的資料庫 volume。

#### Scenario: 匯入真實店家
- **WHEN** 以 `DATASET=real` 與匯出檔目錄啟動空的 real 資料庫
- **THEN** `cafes` 為真實店家且每家都有匯出檔中的經緯度，屬性投票沒有 `user` 來源，會員與行為資料全部是模擬產生

#### Scenario: 外縣市店家
- **WHEN** 匯出檔中有台中市的店家與它的投票
- **THEN** 該店家與投票都不匯入，匯入報告列出排除家數

#### Scenario: 未指定模式
- **WHEN** 未設定 `DATASET`
- **THEN** 使用模擬資料集，匯入服務略過

#### Scenario: 匯入中途失敗
- **WHEN** 寫入店家後、產生行為資料前發生錯誤
- **THEN** 整批 rollback，資料庫維持空的，backend 不啟動

#### Scenario: 重複啟動
- **WHEN** real 資料庫已有店家時再次啟動
- **THEN** 匯入略過，資料不變
