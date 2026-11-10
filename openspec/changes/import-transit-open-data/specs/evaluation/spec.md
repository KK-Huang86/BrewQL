## ADDED Requirements

### Requirement: 交通跨來源題目
golden set SHALL 包含需要串接 YouBike 或捷運資料與 Find Coffee 資料的題目（至少 2 題，含 1 題 hard），標準答案以 demo 資料計算。加入後 SHALL 以 static 與 rag 各執行評估並記錄正確率與每題 token。

#### Scenario: 沒有捷運站的行政區
- **WHEN** 評估「沒有捷運站的行政區中，搜尋次數最多的前 3 區」
- **THEN** 參考 SQL 串接 `search_logs` 與 `mrt_stations`，沒有捷運站的區不因 join 而消失，`--dry-run` 可執行
