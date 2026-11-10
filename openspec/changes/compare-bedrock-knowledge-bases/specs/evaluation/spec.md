## ADDED Requirements

### Requirement: 檢索器比較
評估 SHALL 能以不同檢索器（pgvector、Bedrock Knowledge Bases）跑同一測試集，報告 SHALL 記錄使用的檢索器；比較摘要 SHALL 另列每題兩邊檢索到的知識文件差異與檢索延遲。

#### Scenario: 檢索器比較報告
- **WHEN** 比較 pgvector 與 Knowledge Bases 兩份 `rag` 報告
- **THEN** 摘要列出正確率、成本與檢索延遲差異，以及兩邊檢索結果不同的題目
