## Context

動機見 proposal.md。此時已有完整的 Demo 資料與 static 模式的評估基準。

## Goals / Non-Goals

**Goals:** 可量化的 RAG 前後差異；匯入可重複執行；檢索展示 `asyncio.gather`。

**Non-Goals:** 檢索資料列內容、重排序（rerank）、混合檢索（BM25 + 向量）、自動從 schema 產生文件。

## Decisions

### D1. 檢索的是「關於資料的知識」，不是資料本身
資料列不送給模型：保護個資、prompt 大小不隨資料量成長、數字由資料庫計算不會幻覺。

### D2. Embedding：Bedrock Titan Text Embeddings V2（1024 維）透過 boto3
Anthropic 沒有 embedding 模型；Titan 在同一個 Bedrock 帳號內、價格極低。模型 ID 放設定。boto3 為同步呼叫，同樣以 `asyncio.to_thread` 執行。

### D3. 問題只向量化一次，三類檢索並發
embedding 呼叫最慢，只做一次；三個 pgvector 查詢以 `asyncio.gather` 並發，各自用連線池的連線。

### D4. 匯入的冪等與原子性
每份文件記錄內容雜湊；雜湊相同就跳過 embedding。先在記憶體算好所有向量，再用單一 transaction 做 upsert 與刪除，任何錯誤整批 rollback。

### D5. 權限分離
匯入用專用角色，只能寫知識庫資料表；API 的唯讀角色可讀知識庫（檢索用），但知識庫不在 SQL 白名單，模型產生的 SQL 無法查詢它。

### D6. 模式開關而非直接替換
保留 static 模式，才能在同一套測試集上比較，也能在 RAG 出問題時快速退回。

### D7. 相似度用 cosine distance，先不建向量索引
文件數量只有數十份，全表掃描即可；之後量大再加 HNSW 索引。

## Risks / Trade-offs

- [RAG 後正確率沒提升] → 這也是有價值的結果；依對錯翻轉清單分析原因，調整文件或 top-N
- [範例與測試題相似造成虛高] → 評估前自動檢查完全相同；高度相似由人工審查並記錄
- [檢索漏掉必要欄位] → schema 文件以「每張表一份」為單位，top-N 可調
