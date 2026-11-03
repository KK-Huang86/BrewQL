## ADDED Requirements

### Requirement: 模式比較
評估 SHALL 能指定說明來源模式執行，報告 SHALL 記錄使用的模式；並 SHALL 提供比較兩份報告的摘要（各難度正確率差異、成本與延遲差異、對錯翻轉的題目清單）。

#### Scenario: 比較報告
- **WHEN** 比較 `static` 與 `rag` 兩份報告
- **THEN** 產出差異摘要，列出從錯變對與從對變錯的題目

### Requirement: 防止洩題
任何 `example` 知識的問題 MUST NOT 與黃金測試集的題目相同或高度相似；評估開始前 SHALL 檢查並在發現時報錯停止。

#### Scenario: 範例與測試題重複
- **WHEN** 某份範例的問題與某道測試題完全相同
- **THEN** 評估報錯並指出兩者
