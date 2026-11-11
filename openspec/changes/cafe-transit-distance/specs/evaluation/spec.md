## ADDED Requirements

### Requirement: 距離題目
golden set SHALL 包含需要 `v_cafe_transit` 的題目（至少 2 題，含 1 題 hard），標準答案以 demo 資料計算。加入後 SHALL 以 static 與 rag 各執行評估，記錄正確率、每題 token，以及距離題目是否檢索到 `v_cafe_transit` 的說明。

#### Scenario: 捷運站附近的工作友善咖啡店
- **WHEN** 評估「捷運站步行 5 分鐘內的工作友善咖啡店有幾家」
- **THEN** 參考 SQL 串接 `cafes` 與 `v_cafe_transit`，以 `mrt_distance_m <= 400` 篩選，`--dry-run` 可執行
