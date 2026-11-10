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
- [x] 2.3 實作 Titan embedding client（`to_thread`、模型 ID 設定）並實際匯入；驗證：知識庫筆數等於文件數，重跑不呼叫 embedding
  - 結果：`app/embeddings.py` 的 `TitanEmbedder`（`invoke_model` 放 `to_thread`、`dimensions` 1024、`normalize`、逾時 3／5 秒、最多 2 次）；`scripts/import_knowledge.py`（無效文件 exit 2、不呼叫 embedding；匯入失敗 exit 1）；設定 `EMBEDDING_MODEL_ID`、`KNOWLEDGE_DATABASE_URL`；compose 新增 `tools` profile 的 `knowledge-import` 服務，image 帶入 `knowledge/`。單元測試 10 個紅轉綠（紅燈原因為模組不存在）。實際匯入：`added=30`；重跑 `unchanged=30`、不呼叫 embedding；資料庫 schema 9、glossary 8、example 13，皆 1024 維。抽查最近的 glossary：活躍使用者比例的範例對到「活躍使用者」，但「搜尋不到店的關鍵字」對到「收藏很少／很多」而不是「搜尋落空率」，檢索品質留待 4.2 評估。部署主機的 Titan 權限已列在 `deploy-public-demo` design

## 3. 檢索與流程

- [x] 3.1 測試 + 實作：檢索（單次向量化、三類並發、top-N、空知識庫）；驗證：測試由紅轉綠，含並發耗時測試
  - 結果：`app/retrieval.py`：`Retriever` 向量化一次、`asyncio.gather` 三個查詢；`PgVectorSearch` 以 `genbi_reader` 在唯讀 transaction 內依 cosine distance 排序（pool 3 條連線讓三個查詢真的並行、`statement_timeout` 2 秒）；任何失敗轉成 `RetrievalUnavailable`。單元測試 10 個（只向量化一次、各類 top-N、依類別分組、並發耗時 < 0.25 秒（循序需 0.3 秒）、空知識庫、embedding 或查詢失敗、top-N 須 ≥ 1）＋整合測試 2 個（排序與距離、只回傳指定類別）紅轉綠，紅燈原因為模組不存在。實機（Titan + 本機知識庫）4 題的 glossary 第一名都正確：工作友善 0.66、搜尋落空率 0.73、收藏轉換率 0.20、活躍使用者 0.51。觀察：「活躍使用者」題的 schema 前 4 名沒有 `cafe_views`（定義需要它），留待 4.2 評估。後端 582 個測試通過
- [x] 3.2 測試 + 實作：流程的 static／rag 模式、固定規則與白名單名稱保底、`sources`；static 模式的 prompt 與現在逐字相同；驗證：測試由紅轉綠
  - 結果：`SCHEMA_CONTEXT` 拆成 `REPLY_RULES` + `STATIC_KNOWLEDGE`，拆分前後逐字比對相同；`rag_context` 組成規則、全部白名單表名、檢索到的 schema／名詞／範例。流程在輸入防護之後檢索一次（重試共用、被擋下的問題不花 embedding），結果帶 `sources`；`PROMPT_MODE`（`static` 預設／`rag`）、compose 與 `.env.example` 同步。新增測試 16 個紅轉綠（prompt 組成 4、generator 2、流程 6、API 與設定 3＋既有 1），紅燈原因為介面不存在；`test_api.py` 7 個完整回應比對因新增 `sources` 欄位另以 `test:` commit 更新（需求變更）。實機同一題「台北市有幾家工作友善的咖啡店？」：static 3,157 input tokens、rag 2,108（-33%），兩者都答 57 家。後端 597 個測試通過
- [x] 3.4 測試 + 實作：embedding token 與費用計入用量與成本、檢索失敗回 5xx 且不呼叫模型；驗證：測試由紅轉綠
  - 結果：`TitanEmbedder.embed_with_usage` 回傳向量、`inputTextTokenCount` 與模型；檢索結果帶 embedding 用量併入 `AskUsage`；`pricing.py` 新增 Titan V2 每百萬 tokens 0.02 美元（AWS 上線公告，查證 2026-11-10；部分第三方列 0.20 不採用），`cost_usd` 包含 embedding，單價未知時成本為 NULL。指標：`brewql_llm_tokens` 計入 Titan input、成本新增 `embedding` 元件、階段新增 `retrieval`，新 series 從 0 開始。檢索失敗：`unavailable_retrieval` 502「知識檢索暫時無法使用，請稍後再試」，不呼叫產生 SQL 的模型，稽核記錄該種類；告警規則以 `unavailable_.*` 涵蓋，dashboard 說明同步。新增測試 13 個紅轉綠（紅燈原因為介面不存在）；`test_retrieval.py` 的假 embedder 因介面改為 `embed_with_usage` 另以 `test:` commit 更新（需求變更）。實機 rag 一題：指標 embedding 成本 0.00000024 美元（12 tokens）、`retrieval` 階段 1.2 秒（第一次含建立連線池與 client）、稽核成本 0.00283534 美元。後端 615 個測試通過
- [x] 3.3 測試：知識庫資料表不在白名單、查詢會被拒絕；驗證：測試綠燈
  - 結果：`tests/test_knowledge_not_queryable.py` 6 個案例（直接查、加 schema 前綴、CTE 內、子查詢都被 SQL 防護拒絕；不在白名單；模型產生的知識庫 SQL 回 `guardrail` 錯誤且不送到資料庫）。驗證型測試一寫就綠；mutation：把 `knowledge_documents` 加進白名單後 6 個全部失敗。資料庫層 `genbi_reader` 可以讀知識庫（檢索需要，2.1 的整合測試已證明），所以白名單是唯一的防線

## 4. 評估

- [x] 4.1 測試 + 實作：評估指定模式、比較摘要、洩題檢查；驗證：測試由紅轉綠
  - 結果：`python -m evaluation --mode static|rag`（未指定時依 `PROMPT_MODE`），rag 模式把檢索器接進評估流程；報告記錄 `prompt_mode` 與每題使用的知識 ID。`evaluation/compare_runs.py` 讀兩份 JSON 報告，輸出各難度正確率、平均輸入 token、平均成本、p50／p95、從錯變對與從對變錯的題目，以及翻轉題目在 rag 使用的知識；兩份報告題目不同時拒絕比較。`evaluation/leaks.py` 在任何付費呼叫前檢查範例問題與測試題（忽略空白與問號）完全相同即停止；repo 中的範例通過檢查。新增測試 13 個紅轉綠（紅燈原因為模組不存在）；`test_eval_report.py` 的完整 JSON 比對因新增欄位另以 `test:` commit 更新（需求變更）。`--dry-run --mode rag` 對測試資料庫執行正常。後端 626 個測試通過
- [ ] 4.2 以真實 Bedrock 分別跑 static 與 rag；驗證：比較摘要記入評估紀錄（各難度正確率、成本、延遲、翻轉題目）
- [ ] 4.3 依 4.2 結果決定預設模式：`rag` 不比 `static` 差才改預設（獨立 commit）；驗證：README 與 `.env.example` 記錄預設與理由
