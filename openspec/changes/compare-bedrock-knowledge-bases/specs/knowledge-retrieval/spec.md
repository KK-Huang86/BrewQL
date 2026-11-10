## ADDED Requirements

### Requirement: 可替換的檢索器
檢索 SHALL 透過同一介面提供，至少有兩個實作：pgvector（正式流程）與 Amazon Bedrock Knowledge Bases（比較用）。兩者 SHALL 回傳相同形狀的結果（三類各前 N 筆，每筆含知識文件 ID 與類型）。Knowledge Bases 實作 MUST NOT 成為正式流程的預設，其雲端資源 MUST 以 Terraform 管理並在比較後銷毀。

#### Scenario: Knowledge Bases 結果對回知識文件
- **WHEN** Knowledge Bases 回傳一筆帶有文件 ID 與類型 metadata 的結果
- **THEN** 檢索結果中的 ID、類型與標題與 repo 中的知識文件相同

#### Scenario: Knowledge Bases 回傳未知文件
- **WHEN** 回傳結果的文件 ID 不存在於 repo 的知識文件
- **THEN** 該筆被忽略並記錄警告，其餘結果照常回傳

#### Scenario: 正式流程預設使用 pgvector
- **WHEN** 未指定檢索器啟動 API
- **THEN** 使用 pgvector 檢索器
