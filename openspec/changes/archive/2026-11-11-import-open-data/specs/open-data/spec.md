## ADDED Requirements

### Requirement: 公開資料快照
系統 SHALL 以固定版本快照提供台北市、新北市的行政區人口與面積（`district_population`）及大專校院（`universities`），每列帶 `city` 與 `district`；兩城市沒有同名行政區，查詢以 `district` 與既有資料串接。快照 SHALL 由腳本從官方檔產生，重跑結果相同；城市寫法 SHALL 統一為「台」。快照 MUST NOT 包含個人資訊（例如校長姓名、電話）。demo 與 real 資料集 SHALL 都載入相同快照。

#### Scenario: 每萬人咖啡店數
- **WHEN** 查詢各行政區店家數除以 `district_population.population`
- **THEN** demo 的每個行政區都有人口資料，結果不因名稱不一致而遺漏

#### Scenario: 重產快照
- **WHEN** 以相同官方檔重跑快照腳本
- **THEN** 產生的檔案內容不變

#### Scenario: 個人資訊
- **WHEN** 檢視大專校院快照
- **THEN** 沒有姓名、電話、傳真欄位

### Requirement: 來源標示
README SHALL 列出每份公開資料的提供機關、資料集網址、資料時間與授權（政府資料開放授權條款第 1 版）。

#### Scenario: 查來源
- **WHEN** 使用者想知道人口數的時間點
- **THEN** README 與 `district_population.as_of` 都寫明資料時間
