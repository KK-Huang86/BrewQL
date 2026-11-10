## ADDED Requirements

### Requirement: 跨資料來源題目
golden set SHALL 包含需要串接公開資料與 Find Coffee 資料的題目（至少 3 題，含 1 題 hard），標準答案以 demo 資料計算。加入後 SHALL 以 static 與 rag 各執行評估並記錄正確率與每題 token。

#### Scenario: 跨來源題目
- **WHEN** 評估「每萬人咖啡店數最高的行政區」
- **THEN** 參考 SQL 串接 `cafes` 與 `district_population`，`--dry-run` 可執行
