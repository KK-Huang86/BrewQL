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
| 2026-11-10 | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | rag 調校：`glossary.yaml` 新增「評分」（沒指明來源的評分就是 Google 評分 `rating`，不要反問）、`examples.yaml` 新增對照範例「各城市咖啡店的平均評分」，共 32 份知識文件，其他同上一列 | 26 | 26/26（easy 6/6、medium 11/11、hard 5/5、refuse 4/4），連跑 2 次相同 | 3,344 ms／4,010 ms | $0.0029～$0.0030 | 調校過程：只加名詞定義時評估 26/26 兩次，但改用另一種問法「平均評分最高的行政區是哪一個？」（無「只列出行政區名稱」）實測 rag 1/3 直接回答、static 3/3；把社群評分項目逐一寫進定義後變成 0/5。印出 prompt 發現最接近的範例是「新北市各行政區的 Cafe Nomad 網路平均評分」，句型相同但用社群評分，範例的影響比定義強。加入用 `rating` 的對照範例、定義改回簡短後同一問法 15/15 直接回答。和 static 比：每題輸入 3,050 → 約 2,240 token（-27%），每題成本 $0.0038 → $0.0029～$0.0030（-22%～-25%），p50 2,079～2,653 ms（static 約 1,840 ms）。rag 不比 static 差（52/52 對 52/52），預設改為 rag（rag-knowledge-base D10）。兩次總成本 $0.0749、$0.0782 |
| 2026-11-10 | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | import-open-data 第一階段 static：資料加入 `district_population`、`universities`（政府公開資料），schema 說明加兩張表與「每萬人咖啡店數」；`PROMPT_MODE=static`、Guardrail v4、`MAX_SQL_RETRIES=1` | 29 | 29/29（easy 6/6、medium 13/13、hard 6/6、refuse 4/4），連跑 2 次相同 | 2,643 ms／4,186 ms | $0.0043～$0.0045 | 新增 q27～q29 跨資料來源題（題數變動，正確率不能直接和上一列比）。每題輸入約 3,630～3,760 token（上一列 static 約 3,050，新表說明與名詞多約 300 token，其餘來自重試）。第一次 q21 重試 1 次後答對。p50 1,885／1,764 ms。兩次總成本 $0.1307、$0.1261 |
| 2026-11-10 | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | import-open-data 第一階段 rag：36 份知識文件（新增兩張表的 schema、「每萬人咖啡店數」、範例「新北市每萬人咖啡店數」），其他同上一列 | 29 | 29/29（easy 6/6、medium 13/13、hard 6/6、refuse 4/4），連跑 2 次相同 | 4,011 ms／3,733 ms | $0.0030 | 調校過程：第一版說明寫「以 city + district 串接」，rag 兩次都是 27/29：q19 多回一欄 city，q08 反問要查哪個城市；檢索第一名是 `schema-district_population`，城市加行政區的寫法讓模型把城市也當成分組條件。雙北 41 區沒有同名區，說明改成「以 district 串接」後 q08、q19 等 7 題連跑 2 次全對，完整評估兩次 29/29。和 static 比：每題輸入約 2,340 token（-36%），每題成本 -30%，p50 2,186／2,132 ms（static 約 1,800 ms）。兩次總成本 $0.0858、$0.0862 |
| 2026-11-11 | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | import-transit-open-data static：資料加入 `youbike_stations`、`mrt_stations`（政府公開資料，以行政區串接），schema 說明加兩張表與「交通便利度」；`PROMPT_MODE=static`、Guardrail v4、`MAX_SQL_RETRIES=1` | 31 | 31/31（easy 6/6、medium 14/14、hard 7/7、refuse 4/4），連跑 2 次相同 | 2,565 ms／3,978 ms | $0.0050 | 新增 q30、q31 交通題（題數變動，正確率不能直接和上一列比）。每題輸入約 4,095 token（第一階段 static 約 3,630～3,760，兩張表與名詞多約 400 token）。p50 1,862／1,898 ms。兩次總成本 $0.1560、$0.1558 |
| 2026-11-11 | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | import-transit-open-data rag：39 份知識文件（新增兩張表的 schema、「交通便利度」；範例已達 15 份上限，不新增），其他同上一列 | 31 | 第一版 31/31、30/31；調整後 31/31，連跑 2 次相同 | 3,915 ms／3,676 ms | $0.0030～$0.0033 | 第一版第二次 q21（搜尋前 5 區中落空率最高的區）兩次產生的 SQL 都執行失敗。檢索比對：加入 3 份交通文件後，31 題中有 14 題至少取回 1 份交通文件，不相關的題目也會取到（例如 q01「台北市有幾家咖啡店」的 schema 前 4 名有兩張交通表），其中 q19、q29 擠掉了「每萬人咖啡店數」名詞。調整：schema 說明拿掉「台北市、新北市」與「cafes、search_logs」等通用字眼，名詞改寫成以站點表為主，被擠掉的文件從 19 次降為 16 次。q21 單題 rag 重跑：沒有交通文件 5/5，有交通文件（調整前後）各 3/5～4/5；q21 的名詞前 3 名中，交通名詞擠掉的是不相關的「收藏很少／很多」，失敗原因是模型把彙總寫在外層查詢，之前的評估也需要重試，判斷為原本就不穩定的題目，交通文件可能增加干擾，留給 `model-comparison-report` 處理。和 static 比：每題輸入約 2,310～2,480 token（-40%），每題成本 -36%，p50 2,189／2,126 ms。調整後兩次總成本 $0.0943、$0.1024 |
| 2026-11-11 | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | cafe-transit-distance static：`cafes` 加 `lat`、`lng`，新增 view `v_cafe_transit`（最近捷運站、直線距離、300 公尺內 YouBike 站數）與「捷運站附近」名詞；`PROMPT_MODE=static`、Guardrail v4、`MAX_SQL_RETRIES=1` | 33 | 33/33（easy 6/6、medium 15/15、hard 8/8、refuse 4/4），連跑 2 次相同 | 2,582 ms／2,521 ms | $0.0055 | 新增 q32、q33 距離題（題數變動，正確率不能直接和上一列比）。每題輸入約 4,498 token（上一列 static 約 4,095，+約 400）。沒有任何題目自己用經緯度算距離，距離題都用 view。p50 1,770／1,782 ms。兩次總成本 $0.1814、$0.1812 |
| 2026-11-11 | `us.anthropic.claude-haiku-4-5-20251001-v1:0` | cafe-transit-distance rag：41 份知識文件（新增 `schema-v_cafe_transit`、`glossary-near-mrt`，範例維持 15 份），其他同上一列 | 33 | 33/33（easy 6/6、medium 15/15、hard 8/8、refuse 4/4），連跑 2 次相同 | 2,614 ms／2,372 ms | $0.0032 | 檢索：q32、q33 的 schema 第一名都是 `schema-v_cafe_transit`、名詞第一名都是 `glossary-near-mrt`，q32 仍取到需要的「工作友善」。其他 31 題只有 5 題取到距離文件（上一個 change 的交通文件是 14/31），名詞只加一份是刻意的。q21 四次都答對。和 static 比：每題輸入約 2,381 token（-47%），每題成本 -42%，p50 2,156／1,957 ms。兩次總成本 $0.1042、$0.1043 |
