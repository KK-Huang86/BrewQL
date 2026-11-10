# 評估紀錄

這裡記錄重要的評估結果，例如基準線、RAG 前後、模型比較。每次執行的完整報告在 `backend/evaluation/reports/`，不進版控；這份文件是人工整理的摘要，也是面試時引用數據的來源。

## 怎麼跑

```bash
# 只檢查參考 SQL，不呼叫模型（免費）
uv --directory backend run python -m evaluation --dry-run

# 完整評估（會呼叫 Bedrock 與 Guardrail，15 題約 US$0.03）
uv --directory backend run python -m evaluation
```

需要和 API 相同的設定：AWS 憑證、`BEDROCK_*`，以及以 `genbi_reader` 連線的 `DATABASE_URL`。

## 怎麼記

一次執行記一列。欄位：

| 欄位 | 內容 |
|---|---|
| 日期 | 執行日期（UTC） |
| 模型 | Bedrock 模型 ID |
| 設定 | 會影響結果的設定，例如 Guardrail 版本、`MAX_SQL_RETRIES`、有沒有 RAG、prompt 改動 |
| 題數 | 這次跑了幾題 |
| 正確率 | 答對題數／總題數，並列出 easy／medium／hard／refuse 各自的結果 |
| p95 | 回應時間 p95 |
| 每題成本 | 平均每題美元，包含模型 token 與 Guardrail |
| 備註 | 答錯的題號與原因、和上一列比較的結論 |

規則：

- 只記錄值得比較的執行，不是每次都要記。
- 比較兩次執行時，除了要比較的那一項，其他設定要相同；不同時寫在備註。
- 模型輸出不是固定的，重要的比較要跑 2 次，取平均或兩次都記。
- 題目有增減時，在備註註明，正確率不能直接和舊的比較。

## 紀錄

| 日期 | 模型 | 設定 | 題數 | 正確率 | p95 | 每題成本 | 備註 |
|---|---|---|---|---|---|---|---|
| 2026-11-07 | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | 基準線：Guardrail v1、`MAX_SQL_RETRIES=1`、無 RAG、資料只有 `cafes` | 15 | 14/15（easy 5/5、medium 3/4、hard 2/2、refuse 4/4） | 2,607 ms | $0.0017 | 誤擋 1 題：q09（2025 年每月新上架）被模型以「無法預測未來」拒答，模型不知道今天的日期，把 2025 年當成未來。q14 prompt injection 由輸入 Guardrail 擋下（0 次模型呼叫）。沒有題目觸發重試。總成本 $0.0257 |
| 2026-11-07 | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | 同基準線，system prompt 加上今天日期（台北時間）與歷史資料說明 | 15 | 15/15（easy 5/5、medium 4/4、hard 2/2、refuse 4/4），連跑 2 次相同 | 2,564 ms／2,928 ms | $0.0018 | q09 修正：2025 年被當成歷史資料查詢。q13「預測下個月」仍正確拒答，日期說明沒有讓預測題被誤放行。日期說明讓每題輸入多約 60 token（約 +$0.0001）。兩次總成本 $0.0266、$0.0266 |
| 2026-11-08 | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | ticket 6：資料加入 `users`、`search_logs`、`v_daily_activity`，schema 說明加新表與時間用語；Guardrail v4（只保留 prompt attack，拿掉 off-topic 拒絕話題）；`MAX_SQL_RETRIES=1`、無 RAG | 18 | 18/18（easy 5/5、medium 6/6、hard 3/3、refuse 4/4），連跑 2 次相同 | 2,648 ms／3,075 ms | $0.0023 | 新增 q16～q18 趨勢題（題數變動，正確率不能直接和上一列比）。q12、q13 由模型拒答；q14 prompt injection 仍由 Guardrail 擋下（0 次模型呼叫）；q15 仍反問。每題輸入約 1,690 token（上一列約 1,108，新資料表的 schema 說明多約 580 token），Guardrail 只計 content units，topic units 為 0。每題成本上升約 $0.0005，主要來自 schema 說明變長，ticket 9 RAG 只取相關資料表可望降低。兩次總成本 $0.0416、$0.0418 |
| 2026-11-09 | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | ticket 7：搜尋依行政區加權（內湖區供給缺口）；schema 說明加「搜尋落空率」定義與「比較或排名題只回一個類別欄與一個主要指標欄」；Guardrail v4、`MAX_SQL_RETRIES=1`、無 RAG | 21 | 21/21（easy 5/5、medium 8/8、hard 4/4、refuse 4/4），連跑 2 次相同 | 2,068 ms／2,416 ms | $0.0025 | 新增 q19～q21 行政區比較題（題數變動，正確率不能直接和上一列比）；q21（前 5 名中落空率最高）答內湖區。比較題提示沒有讓既有 18 題退步，也沒有題目觸發重試。每題輸入約 1,813 token（上一列約 1,690，多出的是落空率定義與比較題提示）。兩次總成本 $0.0515、$0.0519 |
| 2026-11-09 | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | ticket 8（**RAG 前的最終基準**）：資料加入 `cafe_views`、`favorites`、`cafe_nomad_cache`、`cafe_attribute_votes`、`v_cafe_profile`，`cafes` 加收藏與瀏覽數；schema 說明加新表與「收藏轉換率」（含 SQL 範本）、「活躍使用者」、「收藏很少」定義；Guardrail v4、`MAX_SQL_RETRIES=1`、無 RAG | 26 | 26/26（easy 6/6、medium 11/11、hard 5/5、refuse 4/4），連跑 2 次相同 | 3,791 ms／3,360 ms | $0.0038／$0.0040 | 新增 q22～q26 瀏覽、收藏與社群評分題（題數變動，正確率不能直接和上一列比）；q22 轉換率題需要兩張表。瀏覽器實測時模型曾把瀏覽和收藏 JOIN，轉換率算成 18.1%（應為 11.5%），定義改成 SQL 範本並註明不要 JOIN 後修正。每題輸入約 3,050～3,180 token（上一列約 1,813，多約 70%），每題成本上升約 55%；p95 上升主要來自 q21、q04 單題偏慢。ticket 9 RAG 以這一列比較成本與正確率。兩次總成本 $0.0997、$0.1039 |
| 2026-11-10 | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | rag-knowledge-base 的 static 對照組：同 ticket 8 基準，`PROMPT_MODE=static`；Guardrail v4、`MAX_SQL_RETRIES=1` | 26 | 26/26（easy 6/6、medium 11/11、hard 5/5、refuse 4/4），連跑 2 次相同 | 6,132 ms／2,887 ms | $0.0038 | prompt 拆成固定規則＋知識後逐字不變，結果與 ticket 8 基準一致。p50 1,860／1,821 ms；第一次 p95 偏高來自 q24（7.5 秒）、q20（6.1 秒）單題。每題輸入約 3,050 token。兩次總成本 $0.0995、$0.0998 |
| 2026-11-10 | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | rag-knowledge-base：`PROMPT_MODE=rag`（Titan V2 1024 維、schema 前 4、名詞前 3、範例前 3；30 份知識文件），其他同上一列 | 26 | 26/26 與 25/26（第二次 medium 10/11） | 3,038 ms／4,134 ms | $0.0029 | 和 static 比：每題輸入 3,050 → 2,184 token（-28%），每題成本 $0.0038 → $0.0029（-25%，含 embedding 約 12 token），p50 1,860 → 2,070 ms（+約 200 ms，多一次 Titan 呼叫與向量查詢）。第二次 q08「平均評分最高的行政區」被反問「Google 評分還是 Cafe Nomad 評分」：兩次檢索結果相同，排在前面的是 `v_cafe_profile`、`cafe_nomad_cache` 與「新北市網路評分」範例，static 的 cafes 說明則先寫 `rating：Google 評分`，rag 少了「評分未指明時指 Google 評分」的提示。兩次總成本 $0.0747、$0.0752 |
| 2026-11-10 | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | rag 調校：`glossary.yaml` 新增「評分」（沒指明來源時指 Google 評分 `rating`，社群評分只在明確提到網路、座位等時使用），共 31 份知識文件，其他同上一列 | 26 | 26/26（easy 6/6、medium 11/11、hard 5/5、refuse 4/4），連跑 2 次相同 | 3,706 ms／3,431 ms | $0.0030 | q08 兩次都檢索到「評分」並直接回答，上一列的反問消失。和 static 比：每題輸入 3,050 → 約 2,250 token（-26%），每題成本 $0.0038 → $0.0029～$0.0030（-22%～-25%），p50 約 2,080 ms（static 約 1,840 ms）。rag 不比 static 差（52/52 對 52/52），預設改為 rag（rag-knowledge-base D10）。兩次總成本 $0.0749、$0.0785 |
