## ADDED Requirements

### Requirement: 真實店家資料集模式
系統 SHALL 支援 `DATASET=real` 模式，從 repo 外的本機匯出檔匯入真實店家的公開欄位、google 與 cafenomad 來源的屬性投票、以及比對得到店家的 Cafe Nomad 資料。欄位 SHALL 以白名單挑選。匯入 MUST NOT 包含任何會員或行為資料及其彙總（會員、搜尋、瀏覽、收藏、使用者投票、`favorite_count`、`view_count`）；行為資料 SHALL 以模擬方式依真實店家產生。只有城市為台北市或新北市的店家 SHALL 被匯入（位置可由經緯度補上）；其他縣市與位置未知的店家，連同它們的投票，MUST NOT 被匯入。預設模式 MUST 為 `demo`，兩種模式 SHALL 使用各自的資料庫 volume。

#### Scenario: 匯入真實店家
- **WHEN** 以 `DATASET=real` 與匯出檔目錄啟動空的 real 資料庫
- **THEN** `cafes` 為真實店家，屬性投票沒有 `user` 來源，會員與行為資料全部是模擬產生

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

### Requirement: 地址解析城市與行政區
匯入 SHALL 由地址解析 `city` 與 `district`，城市寫法統一為 demo 使用的「台」。無法解析時 SHALL 沿用 1 公里內最近的已解析店家；仍無法判斷時 SHALL 為 NULL，並在匯入報告列出家數。

#### Scenario: 臺與台
- **WHEN** 地址為「臺北市大安區…」
- **THEN** `city` 為「台北市」、`district` 為「大安區」

#### Scenario: 地址缺城市
- **WHEN** 地址無法解析，且 1 公里內有已解析的店家
- **THEN** 沿用該店家的城市與行政區

### Requirement: 評估固定使用模擬資料
golden set 評估與 CI MUST 只在模擬資料集上執行，確保標準答案可重現。評估開始前 SHALL 確認資料庫是 demo，否則在任何付費呼叫前報錯停止。

#### Scenario: CI 執行評估
- **WHEN** CI 執行評估
- **THEN** 資料庫為模擬資料集

#### Scenario: 對 real 資料庫執行評估
- **WHEN** 資料庫含有非 demo 店家時執行評估
- **THEN** 評估報錯停止，沒有呼叫 Bedrock

### Requirement: 真實資料不進版本控制
匯入檔與真實店家資料 MUST NOT 被 commit 到 repo。

#### Scenario: 誤加匯入檔
- **WHEN** 匯入檔被複製到 `db/import/` 下並執行 `git status`
- **THEN** 該檔案被 `.gitignore` 忽略
