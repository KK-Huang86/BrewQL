## Why

Text-to-SQL 最常錯的不是語法，而是模型不懂業務定義（例如「工作友善」）與欄位意義。目前把整份說明塞進 prompt：資料表越多越貴、越容易混淆。改用 RAG 只取與問題相關的欄位說明、名詞定義與 SQL 範例，並用評估數據證明「加入 RAG 前後正確率差多少」——這是整個專案最有說服力的一組數字。

## What Changes

- 知識庫：在 repo 中手寫三類文件（欄位說明、商業名詞定義、問題與 SQL 範例），不包含任何資料列內容
- 匯入：用 Bedrock Titan Text Embeddings 向量化後寫入 pgvector；可重複執行且結果相同
- 檢索：問題向量化一次，以 `asyncio.gather` 同時檢索三類知識各取前幾筆
- 流程：可設定使用「固定說明」或「RAG」，回應附上使用了哪些知識
- 評估：同一測試集比較兩種模式，記錄差異

## Capabilities

### New Capabilities

- `knowledge-retrieval`: 知識文件的管理、向量化匯入與相似度檢索。

### Modified Capabilities

- `query-pipeline`: 支援以檢索結果組成給模型的說明，並回報使用的知識。
- `evaluation`: 支援依設定比較兩種模式，並防止測試題洩漏到範例中。

## Impact

- 新增：知識文件、匯入程式、檢索模組、知識庫寫入角色
- 新依賴：boto3（呼叫 Titan Embeddings）
- 成本：匯入約數十份短文件、每題多一次 embedding 呼叫，費用可忽略
- 依賴 ticket：`eval-golden-set`、`view-favorite-insights`
