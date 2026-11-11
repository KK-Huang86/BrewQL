## MODIFIED Requirements

### Requirement: 公開資料快照
系統 SHALL 以固定版本快照提供台北市、新北市的行政區人口與面積（`district_population`）、大專校院（`universities`）、營運中的 YouBike 2.0 站點（`youbike_stations`）與臺北捷運車站（`mrt_stations`），每列帶 `city` 與 `district`；兩城市沒有同名行政區，查詢以 `district` 與既有資料串接。快照 SHALL 由腳本從官方檔產生，重跑結果相同；城市寫法 SHALL 統一為「台」，每個 `district` SHALL 是 `district_population` 中的行政區。快照 MUST NOT 包含個人資訊（例如校長姓名、電話）與即時欄位（例如可借車輛數）。YouBike 與捷運快照 SHALL 保留站點經緯度。demo 與 real 資料集 SHALL 都載入相同快照。

#### Scenario: 每萬人咖啡店數
- **WHEN** 查詢各行政區店家數除以 `district_population.population`
- **THEN** demo 的每個行政區都有人口資料，結果不因名稱不一致而遺漏

#### Scenario: 重產快照
- **WHEN** 以相同官方檔重跑快照腳本
- **THEN** 產生的檔案內容不變

#### Scenario: 個人資訊
- **WHEN** 檢視大專校院快照
- **THEN** 沒有姓名、電話、傳真欄位

#### Scenario: 非行政區的 YouBike 區域
- **WHEN** 台北 YouBike 站的 `sarea` 為「臺大公館校區」
- **THEN** 快照中該站的 `district` 為「大安區」

#### Scenario: 捷運車站由出入口整理
- **WHEN** 官方檔有「頂埔站出口1」至「頂埔站出口4」與「台北車站M1」至「台北車站M8」
- **THEN** 快照各有一列「頂埔」與「台北車站」，座標為出入口平均，`exit_count` 為出入口數

#### Scenario: 各區交通站數
- **WHEN** 查詢各行政區咖啡店數與 `youbike_stations`、`mrt_stations` 的站數
- **THEN** 以 `district` 串接，沒有站的行政區站數為 0 而不是被排除

### Requirement: 來源標示
README SHALL 列出每份公開資料的提供機關、資料集網址、資料時間與授權（政府資料開放授權條款第 1 版）。即時資料的快照 SHALL 以下載日為資料時間。

#### Scenario: 查來源
- **WHEN** 使用者想知道人口數的時間點
- **THEN** README 與 `district_population.as_of` 都寫明資料時間

#### Scenario: 即時資料的時間點
- **WHEN** 使用者想知道 YouBike 站數的時間點
- **THEN** README 與 `youbike_stations.as_of` 都寫明下載日
