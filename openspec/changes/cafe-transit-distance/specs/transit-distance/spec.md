## ADDED Requirements

### Requirement: 店家到交通站點的距離
系統 SHALL 提供 view `v_cafe_transit`，每家有座標的店一列，欄位為 `cafe_id`、最近的捷運站 `nearest_mrt`、到該站的直線距離 `mrt_distance_m`（公尺，haversine），以及直線距離 300 公尺內的 YouBike 站數 `youbike_within_300m`。距離 SHALL 以 `cafes` 與 `mrt_stations`、`youbike_stations` 的經緯度計算，不得使用外部服務。`genbi_reader` SHALL 可以查詢此 view。

#### Scenario: 已知距離
- **WHEN** 一家店與某捷運站的座標相距約 500 公尺，且沒有更近的捷運站
- **THEN** `nearest_mrt` 為該站，`mrt_distance_m` 與 500 的誤差小於 1%

#### Scenario: 附近的 YouBike
- **WHEN** 一家店 300 公尺內有 2 個 YouBike 站、350 公尺處有 1 個
- **THEN** `youbike_within_300m` 為 2

#### Scenario: 查詢時間
- **WHEN** 在 real 模式查詢整個 `v_cafe_transit`
- **THEN** 在 statement timeout 內完成

### Requirement: 距離名詞
知識文件 SHALL 定義「捷運站附近／步行 5 分鐘」為 `mrt_distance_m <= 400`、「附近有 YouBike」為 `youbike_within_300m > 0`，並說明距離是直線距離；距離問題 SHALL 指示模型使用 `v_cafe_transit`，而不是以 `lat`、`lng` 自行計算。

#### Scenario: 捷運站附近的不限時咖啡店
- **WHEN** 使用者問「捷運站步行 5 分鐘內的不限時咖啡店有幾家」
- **THEN** 產生的 SQL 以 `v_cafe_transit.mrt_distance_m <= 400` 篩選，不自行計算經緯度距離
