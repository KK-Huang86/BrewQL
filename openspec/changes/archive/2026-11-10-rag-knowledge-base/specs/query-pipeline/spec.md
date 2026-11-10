## ADDED Requirements

### Requirement: 說明來源模式
系統 SHALL 支援兩種給模型說明的模式，由設定切換：`static`（固定的完整說明）與 `rag`（依檢索結果組成）。`rag` 模式下說明 SHALL 一律包含固定的回覆規則（回覆類型、拒答與反問條件）、白名單資料表名稱清單與今天日期，即使檢索結果為空；檢索到的知識接在後面。預設模式為 `rag`（評估證明 `rag` 不比 `static` 差後以獨立 commit 切換，數據記於評估紀錄）；`static` 保留為退回選項，切到 `static` 時啟動流程 MUST NOT 依賴 embedding 服務。

#### Scenario: RAG 模式
- **WHEN** 模式為 `rag`
- **THEN** 給模型的說明由檢索到的知識組成，不包含未被檢索到的名詞定義

#### Scenario: 檢索結果為空
- **WHEN** 模式為 `rag` 且檢索不到任何知識
- **THEN** 說明仍包含白名單資料表名稱，流程正常進行

### Requirement: 檢索的成本與故障
`rag` 模式下檢索成功時，問題向量化的 token 數與費用 SHALL 計入該題的用量與估算成本（指標、稽核紀錄與評估報告同一來源）；檢索失敗時與其他相依服務故障相同，只記錄故障種類與耗時。Embedding 或檢索失敗 SHALL 視為相依服務故障回應 5xx，並以獨立的故障種類記錄；MUST NOT 靜默改用 `static` 模式。

#### Scenario: 成本包含 embedding
- **WHEN** 以 `rag` 模式回答一題
- **THEN** 該題的估算成本包含 embedding 費用

#### Scenario: embedding 失敗
- **WHEN** Titan embedding 呼叫失敗
- **THEN** 回應 5xx，故障種類為檢索，不呼叫產生 SQL 的模型

### Requirement: 回報使用的知識
`rag` 模式下回應 SHALL 包含 `sources`：本次使用的知識 ID、類型與標題；`static` 模式下 `sources` 為空清單。

#### Scenario: 回報來源
- **WHEN** 以 `rag` 模式回答涉及「工作友善」的問題
- **THEN** `sources` 包含「工作友善」的 glossary 文件
