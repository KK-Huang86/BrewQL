## 1. 知識文件

- [x] 1.1 測試 + 實作：知識文件載入與驗證（ID 重複、類型、範例 SQL 通過防護並可執行）；驗證：測試由紅轉綠
  - 結果：`app/knowledge.py` 讀 `schema.yaml`、`glossary.yaml`、`examples.yaml`（範例的問題作為標題、SQL 作為內容）；`tests/test_knowledge_documents.py` 18 個案例紅轉綠（紅燈原因為模組不存在）：跨類型 ID 重複、範例 SQL 被防護拒絕（白名單外、寫入、多敘述、無法解析）、缺欄位、多餘欄位、非清單、YAML 錯誤、檔案不存在（避免被當成刪除全部）；空清單 `[]` 允許。`pyyaml` 改為正式依賴。範例 SQL「可執行」需要資料庫，於 1.2 以整合測試對真實文件逐一執行。後端 483 個測試通過
- [x] 1.2 撰寫知識文件：每張表／view 一份 schema、5 個名詞 glossary、10～15 個範例（不與測試題重複）；驗證：1.1 的驗證通過
  - 結果：`backend/knowledge/` 三個檔案：schema 9 份（7 張表 + 2 個 view，內容與固定說明相同）、glossary 8 個（固定說明的名詞定義與查詢慣例全部搬入）、範例 13 個（會員、收藏排名、關鍵字、落空關鍵字、社群評分、屬性投票、活躍使用者比例等）。`test_knowledge_files.py` 確認每個白名單資料表剛好一份 schema、數量符合；整合測試 `test_knowledge_examples.py` 以 `genbi_reader` 逐一執行範例且都有資料（紅燈原因為 `KNOWLEDGE_DIR` 不存在）。人工審查：沒有範例與 26 題測試題相同；查詢模式相近（例如每月趨勢、評分門檻）但資料表或條件不同，屬於範例該教的寫法。後端 538 個測試通過（含整合測試）

## 2. 匯入

- [x] 2.1 建立知識庫寫入角色並授權；驗證：該角色無法寫入其他資料表
  - 結果：`db/init/05_knowledge.sh` 建立 pgvector extension、`knowledge_documents`（`vector(1024)`、`content_hash`）與 `genbi_knowledge_writer`（只對該表 SELECT／INSERT／UPDATE／DELETE，連線上限 2、`statement_timeout` 30s）；`genbi_reader` 只能 SELECT。整合測試 `test_knowledge_roles.py` 9 個案例紅轉綠（紅燈原因為角色與資料表不存在）：寫入角色可增改刪、碰不到 `cafes`／`ask_audit`、維度不是 1024 被拒；唯讀角色解除唯讀預設後仍不能改、刪、清空。compose、CI、`db/test-db.sh`、`.env.example`、README 同步新密碼變數。後端 547 個測試通過，模擬資料檢查全過
- [x] 2.2 測試 + 實作：匯入（雜湊跳過、更新、刪除、單一 transaction、中途失敗 rollback、錯誤記錄），以假 embedding 測試；驗證：測試由紅轉綠
  - 結果：`app/knowledge_sync.py`：`sync_knowledge` 依雜湊（含模型 ID）決定新增、更新、不變、刪除，所有向量算完才寫入；`PgKnowledgeStore` 以 `genbi_knowledge_writer` 在單一 transaction 內先刪後 upsert，advisory lock 讓同時執行的匯入依序寫入。單元測試 10 個（假 embedder／store）：首次匯入、重跑不呼叫 embedding、只重算變更的文件、刪除、換模型全部重算、範例以問題向量化、第 5 份失敗不寫入並記錄文件 ID 與例外類型、維度錯誤、寫入失敗、空清單刪除全部；整合測試 3 個：增刪後雜湊正確、欄位完整、批次中一筆維度錯誤整批 rollback。紅燈原因為模組不存在。mutation：拿掉 transaction 後 rollback 測試失敗（初版先 upsert 後刪除時抓不到，因 asyncpg `executemany` 本身是原子的，故改為先刪後寫）。後端 560 個測試通過
- [ ] 2.3 實作 Titan embedding client（`to_thread`、模型 ID 設定）並實際匯入；驗證：知識庫筆數等於文件數，重跑不呼叫 embedding

## 3. 檢索與流程

- [ ] 3.1 測試 + 實作：檢索（單次向量化、三類並發、top-N、空知識庫）；驗證：測試由紅轉綠，含並發耗時測試
- [ ] 3.2 測試 + 實作：流程的 static／rag 模式、固定規則與白名單名稱保底、`sources`；static 模式的 prompt 與現在逐字相同；驗證：測試由紅轉綠
- [ ] 3.4 測試 + 實作：embedding token 與費用計入用量與成本、檢索失敗回 5xx 且不呼叫模型；驗證：測試由紅轉綠
- [ ] 3.3 測試：知識庫資料表不在白名單、查詢會被拒絕；驗證：測試綠燈

## 4. 評估

- [ ] 4.1 測試 + 實作：評估指定模式、比較摘要、洩題檢查；驗證：測試由紅轉綠
- [ ] 4.2 以真實 Bedrock 分別跑 static 與 rag；驗證：比較摘要記入評估紀錄（各難度正確率、成本、延遲、翻轉題目）
- [ ] 4.3 依 4.2 結果決定預設模式：`rag` 不比 `static` 差才改預設（獨立 commit）；驗證：README 與 `.env.example` 記錄預設與理由
