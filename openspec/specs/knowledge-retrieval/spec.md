# knowledge-retrieval Specification

## Purpose
以向量檢索找出與問題最相關的欄位說明、商業名詞定義與 SQL 範例，只把需要的知識交給模型，提高 SQL 正確率並控制 prompt 大小。

## Requirements

### Requirement: 知識文件
知識 SHALL 以版本控制中的文件維護，分為 `schema`（資料表／欄位說明）、`glossary`（商業名詞定義）、`example`（問題與 SQL 範例）三類，每份有唯一 ID、類型、標題與內容。知識 MUST NOT 包含資料庫中的資料列內容或任何使用者資料。每份 `example` 的 SQL MUST 能通過 `sql-guardrails` 驗證（匯入時檢查）並以唯讀角色成功執行（整合測試檢查）。

#### Scenario: ID 重複
- **WHEN** 兩份知識文件的 ID 相同
- **THEN** 匯入前報錯停止

#### Scenario: 範例 SQL 不合法
- **WHEN** 某份範例的 SQL 查詢白名單外的資料表
- **THEN** 匯入前報錯並指出該文件

### Requirement: 可重複執行的匯入
匯入 SHALL 為每份文件產生向量並寫入知識庫。重複執行 MUST 得到相同結果：內容未變的文件不重新產生向量；內容變更的文件更新；已刪除的文件從知識庫移除。整批寫入 MUST 在單一 transaction 中完成，任何一份失敗則全部不生效並報告原因。匯入 MUST 使用只能寫知識庫的專用角色。

#### Scenario: 重複執行
- **WHEN** 文件未變更時連續執行兩次匯入
- **THEN** 第二次不呼叫 embedding，知識庫內容不變

#### Scenario: 中途失敗
- **WHEN** 第 5 份文件的 embedding 呼叫失敗
- **THEN** 知識庫維持匯入前的狀態，錯誤被記錄

#### Scenario: 刪除文件
- **WHEN** 從 repo 移除一份文件後重新匯入
- **THEN** 知識庫中不再有該文件

### Requirement: 檢索
給定問題，系統 SHALL 只計算一次問題向量，並同時（並發）檢索三類知識，各回傳相似度最高的前 N 筆（建立檢索器時可指定，預設 schema 4、glossary 3、example 3）。知識庫為空或某類沒有文件時 SHALL 回傳空清單而非錯誤。知識庫資料表 MUST NOT 被加入 SQL 白名單。

#### Scenario: 相關定義被找到
- **WHEN** 問題為「台北市有幾家工作友善的咖啡店？」
- **THEN** glossary 結果包含「工作友善」

#### Scenario: 並發檢索
- **WHEN** 三類檢索各需 100 毫秒
- **THEN** 整體檢索時間明顯小於 300 毫秒

#### Scenario: 知識庫為空
- **WHEN** 尚未匯入任何文件
- **THEN** 三類都回傳空清單

#### Scenario: 模型無法查詢知識庫
- **WHEN** 產生的 SQL 查詢知識庫資料表
- **THEN** 被防護拒絕
