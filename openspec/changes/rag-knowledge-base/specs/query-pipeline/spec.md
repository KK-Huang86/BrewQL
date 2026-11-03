## ADDED Requirements

### Requirement: 說明來源模式
系統 SHALL 支援兩種給模型說明的模式，由設定切換：`static`（固定的完整說明）與 `rag`（依檢索結果組成）。`rag` 模式下說明 SHALL 至少包含白名單資料表名稱清單，即使檢索結果為空。

#### Scenario: RAG 模式
- **WHEN** 模式為 `rag`
- **THEN** 給模型的說明由檢索到的知識組成，不包含未被檢索到的名詞定義

#### Scenario: 檢索結果為空
- **WHEN** 模式為 `rag` 且檢索不到任何知識
- **THEN** 說明仍包含白名單資料表名稱，流程正常進行

### Requirement: 回報使用的知識
`rag` 模式下回應 SHALL 包含 `sources`：本次使用的知識 ID、類型與標題；`static` 模式下 `sources` 為空清單。

#### Scenario: 回報來源
- **WHEN** 以 `rag` 模式回答涉及「工作友善」的問題
- **THEN** `sources` 包含「工作友善」的 glossary 文件
