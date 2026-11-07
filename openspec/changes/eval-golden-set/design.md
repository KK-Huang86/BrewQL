## Context

動機見 proposal.md。此時資料只有 `cafes`，題目先以咖啡店資料為主；之後每個加入資料的 ticket 都要補題目。

ticket 3、4 之後，一次提問的完整流程是：輸入 Guardrail → 模型產生 `{kind, sql, message}` → SQL 防護 → 唯讀執行，失敗最多重試 1 次。評估要量的是這整套系統，所以執行時使用與正式環境相同的設定（輸入 Guardrail 開啟、`MAX_SQL_RETRIES=1`），並把設定記進報告。

## Goals / Non-Goals

**Goals:** 可重複、便宜、結果可比較的評估；明細足以做錯誤分析。

**Non-Goals:** LLM-as-judge、自動錯誤分類（ticket 12 處理）、CI 自動跑評估（會花錢）。

## Decisions

### D1. 執行準確度（execution accuracy）
同一問題有多種正確寫法，比 SQL 字串會低估正確率。比結果才反映使用者真正看到的東西。

### D2. 比較規則：忽略欄位名稱與順序
每列的值先標準化（數值四捨五入 2 位、日期轉字串），再把欄位順序正規化後比較列的多重集合。可能把極少數欄位對調的錯誤答案判為正確，但能避免大量「只是 alias 不同」的誤判；取捨記在報告說明。

### D3. 測試集放 YAML，執行程式放 backend
YAML 好讀好改、可以寫註解；執行程式直接匯入後端的流程模組，評估的就是正式程式碼。

### D4. 結果不進版控，紀錄進版控
每次執行的完整報告輸出到被忽略的目錄；重要的執行（基準、RAG 前後、模型比較）由人手動摘要到評估紀錄文件，作為面試時的數據來源。

### D5. 依序執行，不平行
避免觸發 Bedrock 限流，延遲數據也比較乾淨。15 題約 1～3 分鐘可接受。

### D6. 單價集中在一張價目表
`app/pricing.py` 以模型 ID 對應輸入／輸出每百萬 token 單價，另有 Guardrail 的 denied topic 與 content filter 各自每 1,000 text units 單價，註明來源（Bedrock 官方價格頁）與查詢日期。價格變動只改這一處；`observe-with-grafana` 的成本估算沿用同一張表，評估與線上的成本算法一致。價目表沒有的模型，成本記為未知並在報告標示，不中斷評估。

### D7. 成本包含 Guardrail
每題都會呼叫 ApplyGuardrail，它依 text units 計費（1 unit = 最多 1,000 字元）。輸入 Guardrail 從 ApplyGuardrail 回應的 `usage` 讀取計費 units。實測（tasks 1.1）units 依政策分開計算：`topicPolicyUnits`（denied topic）與 `contentPolicyUnits`（content filter，含 prompt attack），兩者各自計費，所以價目表分開列兩種單價，流程也分開回報。每題成本 = 模型 token 費用 + topic units 費用 + content units 費用。被 Guardrail 擋下的題目沒有 token，但仍有 Guardrail 費用。

### D8. 拒答題不區分來源，但記錄來源
預期 `refused` 的題目，被輸入 Guardrail 擋下或被模型拒答都算正確；明細記錄 `refusal_source`，報告可以看出哪一層擋下。測試集包含一題 prompt injection，觀察 Guardrail 是否在模型之前擋下。

### D9. 題目必須明確
模型遇到模糊問題會反問（ticket 3），反問在一般題會被判錯。因此一般題要寫清楚範圍與條件（例如「台北市各行政區」而不是「各區」），讓錯誤反映 SQL 能力而不是題目本身。參考 SQL 由人撰寫，並以試跑確認可執行。

### D10. 用量只給內部使用
token、Guardrail units 與耗時放在流程結果（`AskResult.usage`），供評估與之後的監控使用；`/api/ask` 回應不包含，避免把成本細節暴露給訪客。

### D11. 檔案位置
評估程式與資料放同一個套件 `backend/evaluation/`，與執行期的 `app/` 分開（評估是開發工具，不會進 API）：
- 測試集：`backend/evaluation/golden.yaml`
- 執行：`uv --directory backend run python -m evaluation [--dry-run] [--only q01,q02]`
- 每次報告：`backend/evaluation/reports/`（不進版控）
- 評估紀錄：`backend/evaluation/RESULTS.md`（進版控，人工摘要）
- `pyyaml` 為 dev 依賴

### D12. 測試集格式
每題：`id`、`question`、`difficulty`（easy / medium / hard / refuse），加上 `sql`（參考 SQL，可選 `ordered: true`）或 `expect`（refused / clarify）二擇一。`refuse` 難度必須用 `expect`，其他難度必須用 `sql`。不認得的欄位視為錯誤，避免 `odered` 這類拼錯被默默忽略。

## Risks / Trade-offs

- [題目太簡單導致正確率虛高] → 刻意放 2 題困難題與 4 題拒答／反問題；資料只有一張表時「困難」有限，ticket 6～8 加資料時補上跨表題
- [Guardrail 計費欄位改變或讀不到] → 欄位已實測確認（tasks 1.1）；回應缺少 `usage` 時 units 記為 0 並在 log 警告，成本標示為不完整
- [之後加的範例 SQL 和測試題重疊造成「洩題」] → ticket 9 的 spec 明訂禁止
- [模型非確定性] → 報告記錄執行時間與設定；重要比較跑 2 次取平均
