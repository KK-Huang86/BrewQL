# evaluation Specification

## Purpose
用固定的黃金測試集對完整流程（輸入 Guardrail、模型、SQL 防護、執行與重試）量化 GenBI 的正確率、拒答能力、延遲與成本，讓每次改動（加資料、RAG、換模型）都能以數據比較好壞。

## Requirements

### Requirement: 黃金測試集
測試集 SHALL 為版本控制中的資料檔，每題包含：編號、問題、難度（easy / medium / hard / refuse）、以及「參考 SQL」或「預期狀態（refused / clarify）」二擇一；可標註結果是否需比對順序。載入時題號重複、缺少必要欄位、或同時有參考 SQL 與預期狀態 MUST 報錯並停止。初始 SHALL 至少 15 題，涵蓋四種難度，其中拒答／反問題至少 4 題（含一題 prompt injection）。

#### Scenario: 題號重複
- **WHEN** 測試集中有兩題編號相同
- **THEN** 評估在呼叫任何模型之前就報錯停止

#### Scenario: 欄位不完整
- **WHEN** 某題沒有參考 SQL 也沒有預期狀態
- **THEN** 報錯並指出該題編號

### Requirement: 以查詢結果判斷對錯
有參考 SQL 的題目，系統 SHALL 以唯讀角色執行參考 SQL，與系統回答的結果比較；結果相同即為正確，不比較 SQL 字串。比較時 SHALL 忽略欄位名稱與欄位順序；數值 SHALL 四捨五入到小數 2 位後比較；未標註需比對順序時 SHALL 忽略列的順序。系統回答 `status` 不是 `ok` 時 MUST 判為錯誤。

#### Scenario: 寫法不同結果相同
- **WHEN** 系統 SQL 用 `COUNT(id)`、參考 SQL 用 `COUNT(*)`，結果都是 42
- **THEN** 判為正確

#### Scenario: 列順序不同
- **WHEN** 未標註需比對順序，兩邊結果列相同但順序不同
- **THEN** 判為正確

#### Scenario: 需比對順序
- **WHEN** 題目標註需比對順序，兩邊結果列相同但順序不同
- **THEN** 判為錯誤

#### Scenario: 浮點誤差
- **WHEN** 系統結果為 4.2300001、參考結果為 4.23
- **THEN** 判為正確

#### Scenario: 系統沒有回答
- **WHEN** 系統回傳 `status=error`
- **THEN** 判為錯誤

### Requirement: 拒答與反問題目
有預期狀態的題目，系統回傳的 `status` 與預期相同時 MUST 判為正確，不同時 MUST 判為錯誤。

#### Scenario: 應拒答
- **WHEN** 預期為 `refused`，系統回傳 `refused`
- **THEN** 判為正確

#### Scenario: 由輸入 Guardrail 擋下
- **WHEN** 預期為 `refused`，系統回傳 `refused`、`refusal_source=input_guardrail`
- **THEN** 判為正確，明細記錄拒答來源

#### Scenario: 該反問卻回答
- **WHEN** 預期為 `clarify`，系統回傳 `ok`
- **THEN** 判為錯誤

### Requirement: 指標與報告
每次評估 SHALL 輸出：整體與各難度正確率、拒答題正確率、p50 與 p95 回應時間、每題平均 token、每題平均成本（依價目表計算，含模型 token 與 Guardrail 費用）、修正次數分布，以及每題的明細（問題、對錯、系統 SQL、參考 SQL、狀態與拒答來源、錯誤訊息、耗時、token、Guardrail units、嘗試次數）。報告 SHALL 有機器可讀與人可讀兩種格式，並記錄模型 ID、Guardrail 是否開啟與版本、`MAX_SQL_RETRIES` 與執行時間。

#### Scenario: 完整報告
- **WHEN** 完成一次評估
- **THEN** 產出 JSON 與 Markdown 報告，含上述所有指標與逐題明細

#### Scenario: 價目表沒有的模型
- **WHEN** 評估使用的模型不在價目表中
- **THEN** 成本記為未知並在報告中標示，評估照常完成

#### Scenario: Guardrail 回應缺少用量
- **WHEN** 某題的 ApplyGuardrail 回應沒有 `usage`
- **THEN** 該題成本記為未知，報告標示成本不完整，評估照常完成

### Requirement: 成本控制
評估 SHALL 在開始前顯示題數與預估呼叫次數，並支援只跑部分題目與不呼叫模型的試跑（只驗證測試集與參考 SQL 可執行）。單題失敗（含服務錯誤）SHALL 記錄後繼續下一題，MUST NOT 中斷整體評估。

#### Scenario: 試跑
- **WHEN** 以試跑模式執行
- **THEN** 不呼叫模型，回報每題參考 SQL 是否可執行

#### Scenario: 未開啟輸入 Guardrail 時的預估
- **WHEN** 評估時未設定輸入 Guardrail
- **THEN** 預估的 Guardrail 檢查次數為 0

#### Scenario: 單題服務錯誤
- **WHEN** 第 3 題呼叫 Bedrock 時發生服務錯誤
- **THEN** 第 3 題記為錯誤並註明原因，評估繼續執行第 4 題

### Requirement: 開跑前檢查資料庫連線設定
評估（含試跑）SHALL 在建立任何資料庫連線前檢查 `DATABASE_URL`：使用者 MUST 為 `genbi_reader`；主機為本機（`localhost`、`127.0.0.1` 或 `::1`）時，port MUST 等於 `DB_PORT`（未設定時為 5434）；URL 未寫 port 時視為 5432。URL 讀不出來（含 port 不是數字）也算不符合。不符合時 SHALL 顯示原因並以非 0 結束，MUST NOT 連線。

#### Scenario: port 指向其他 Postgres
- **WHEN** `DB_PORT=5434` 而 `DATABASE_URL` 連 `127.0.0.1:5432`
- **THEN** 評估在連線前報錯結束，訊息指出 port 與 `DB_PORT` 不符

#### Scenario: port 不是數字
- **WHEN** `DATABASE_URL` 的 port 寫成 `abc`
- **THEN** 評估在連線前報錯結束，不會因例外中斷

#### Scenario: 使用擁有者帳號
- **WHEN** `DATABASE_URL` 的使用者不是 `genbi_reader`
- **THEN** 評估在連線前報錯結束

#### Scenario: 設定正確
- **WHEN** `DATABASE_URL` 以 `genbi_reader` 連 `127.0.0.1:5434` 且 `DB_PORT=5434`
- **THEN** 評估照常執行

### Requirement: 趨勢題
黃金測試集 SHALL 加入至少 3 題涉及 `search_logs` 或 `v_daily_activity` 的趨勢題，其中至少 1 題為困難題。

#### Scenario: 題目可執行
- **WHEN** 以試跑模式執行評估
- **THEN** 新增題目的參考 SQL 都可執行

### Requirement: 行政區比較題
黃金測試集 SHALL 加入至少 3 題行政區比較題，其中至少 1 題涉及搜尋落空率、1 題為困難題（例如「搜尋量前 5 名的行政區中，落空率最高的是哪一區？」）。

#### Scenario: 題目可執行
- **WHEN** 以試跑模式執行評估
- **THEN** 新增題目的參考 SQL 都可執行

### Requirement: 瀏覽與收藏題
黃金測試集 SHALL 加入至少 4 題涉及瀏覽、收藏或社群評分的題目，至少 1 題需要 JOIN 或兩張表（收藏轉換率）、1 題使用 `v_cafe_profile`、1 題涉及「活躍使用者」定義。完成後的完整評估結果 SHALL 記入評估紀錄，標示為加入 RAG 前的基準。

#### Scenario: 題目可執行
- **WHEN** 以試跑模式執行評估
- **THEN** 新增題目的參考 SQL 都可執行

#### Scenario: 題目組成
- **WHEN** 檢查黃金測試集
- **THEN** 至少 4 題查詢 `cafe_views`、`favorites`、`cafe_nomad_cache` 或 `v_cafe_profile`，其中至少 1 題同時用到 `cafe_views` 與 `favorites`

### Requirement: 模式比較
評估 SHALL 能指定說明來源模式執行，報告 SHALL 記錄使用的模式；並 SHALL 提供比較兩份報告的摘要（各難度正確率差異、成本與延遲差異、對錯翻轉的題目清單）。

#### Scenario: 比較報告
- **WHEN** 比較 `static` 與 `rag` 兩份報告
- **THEN** 產出差異摘要，列出從錯變對與從對變錯的題目

### Requirement: 防止洩題
任何 `example` 知識的問題 MUST NOT 與黃金測試集的題目相同或高度相似；評估開始前 SHALL 檢查相同（忽略空白與問號）的題目並在發現時報錯停止，高度相似由新增範例時人工審查。

#### Scenario: 範例與測試題重複
- **WHEN** 某份範例的問題與某道測試題完全相同
- **THEN** 評估報錯並指出兩者

### Requirement: 跨資料來源題目
golden set SHALL 包含需要串接公開資料與 Find Coffee 資料的題目（至少 3 題，含 1 題 hard），標準答案以 demo 資料計算。加入後 SHALL 以 static 與 rag 各執行評估並記錄正確率與每題 token。

#### Scenario: 跨來源題目
- **WHEN** 評估「每萬人咖啡店數最高的行政區」
- **THEN** 參考 SQL 串接 `cafes` 與 `district_population`，`--dry-run` 可執行

### Requirement: 交通跨來源題目
golden set SHALL 包含需要串接 YouBike 或捷運資料與 Find Coffee 資料的題目（至少 2 題，含 1 題 hard），標準答案以 demo 資料計算。加入後 SHALL 以 static 與 rag 各執行評估並記錄正確率與每題 token。

#### Scenario: 店數為 0 的行政區
- **WHEN** 評估「捷運站最多的 3 個行政區，各有幾家咖啡店」，其中一區在 demo 資料沒有咖啡店
- **THEN** 參考 SQL 先各自依 `district` 彙總 `mrt_stations` 與 `cafes` 再 LEFT JOIN，該區店數為 0 而不是消失，`--dry-run` 可執行
