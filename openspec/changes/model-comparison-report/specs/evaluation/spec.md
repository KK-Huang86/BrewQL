## ADDED Requirements

### Requirement: 指定模型評估
評估 SHALL 能以參數指定模型 ID，報告記錄使用的模型；成本 SHALL 依該模型的設定單價計算。未設定單價的模型 MUST 在開始前報錯。

#### Scenario: 指定 Sonnet
- **WHEN** 以 Sonnet 模型 ID 執行評估
- **THEN** 報告的模型欄為 Sonnet，成本依 Sonnet 單價計算

#### Scenario: 未設定單價
- **WHEN** 指定的模型沒有單價設定
- **THEN** 不呼叫任何模型，直接報錯

### Requirement: 錯誤分類
答錯的題目 SHALL 能以人工標註錯誤類型（欄位選錯、名詞理解錯、JOIN 錯誤、時間範圍錯誤、該反問卻回答、其他），標註存於版本控制中的檔案，以題號與報告識別碼對應。報告 SHALL 彙整各類型數量；未標註的錯題 SHALL 列為「未分類」。

#### Scenario: 彙整
- **WHEN** 5 道錯題中 3 道標為「名詞理解錯」、2 道未標註
- **THEN** 報告顯示名詞理解錯 3、未分類 2

#### Scenario: 標註不存在的題號
- **WHEN** 標註檔包含測試集中不存在的題號
- **THEN** 報錯並指出該題號

### Requirement: Prompt caching 量測
送給模型的內容 SHALL 把固定不變的部分（規則、資料表清單、static 模式的完整說明）放在最前面並標記為可快取，會變動的部分（檢索結果、問題、錯誤回饋）放在之後。評估報告 SHALL 記錄快取寫入與快取讀取的 token 數，成本計算 SHALL 依快取讀寫的單價分別計算。固定部分若低於模型的最小快取長度，報告 SHALL 註明快取未生效。

#### Scenario: 連續提問命中快取
- **WHEN** 5 分鐘內連續評估兩題
- **THEN** 第二題的快取讀取 token 大於 0，成本低於未快取時

#### Scenario: 前綴太短
- **WHEN** 固定部分低於最小快取長度
- **THEN** 快取讀取 token 為 0，報告註明原因

### Requirement: 評估報告
版本控制中 SHALL 有一頁評估報告，包含：測試集說明、static 與 rag 的正確率差異、Haiku 與 Sonnet 的正確率／每題成本／p95 延遲比較、prompt caching 前後的每題成本、錯誤類型分布、至少一輪改善措施及改善前後數據、結論（建議預設模型與理由）、限制（題數少、資料為模擬）。README SHALL 連結此報告。

#### Scenario: 報告完整
- **WHEN** 閱讀評估報告
- **THEN** 能找到上述每一項，且數據可對應到評估紀錄中的執行
