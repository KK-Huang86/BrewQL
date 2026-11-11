## ADDED Requirements

### Requirement: 交通跨來源題目
golden set SHALL 包含需要串接 YouBike 或捷運資料與 Find Coffee 資料的題目（至少 2 題，含 1 題 hard），標準答案以 demo 資料計算。加入後 SHALL 以 static 與 rag 各執行評估並記錄正確率與每題 token。

#### Scenario: 店數為 0 的行政區
- **WHEN** 評估「捷運站最多的 3 個行政區，各有幾家咖啡店」，其中一區在 demo 資料沒有咖啡店
- **THEN** 參考 SQL 先各自依 `district` 彙總 `mrt_stations` 與 `cafes` 再 LEFT JOIN，該區店數為 0 而不是消失，`--dry-run` 可執行
