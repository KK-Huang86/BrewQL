## Context

ticket 1 已用 structured outputs 取得 `{sql}`。本 ticket 擴充結果類型，並在模型之前加一道輸入檢查。

## Goals / Non-Goals

**Goals:** 該拒答的不產生 SQL、模糊的會反問、prompt injection 在進入模型前就被攔下。

**Non-Goals:** 輸出端的 Guardrail（SQL 結果是資料庫算的，不是模型生成的文字）、多輪對話式的反問。

## Decisions

### D1. 結果類型放在 JSON schema 裡
`{"kind": "sql" | "refuse" | "clarify", "sql": ..., "message": ...}`。比文字標記可靠；程式再檢查「類型與欄位是否一致」。

### D2. 兩道關卡、各司其職
- **Bedrock Guardrails（輸入）**：擋 prompt attack 與明顯無關的話題，便宜、快、不需要模型推理。
- **SQL 產生模型（語意）**：判斷「要預測未來」「問題太模糊」這類需要理解 schema 與業務的情況。
- **SQL 防護（最後一關）**：就算前兩關都被騙過，SQL 仍不能寫入或讀取禁止的內容。

面試重點：縱深防禦，任何一關被繞過都不會造成資料損失。

### D3. ApplyGuardrail API 獨立呼叫
用 boto3 `apply_guardrail` 單獨檢查問題，而不是把 Guardrail 綁在模型呼叫上。這樣被攔下時連 SQL 產生模型都不用呼叫，也能清楚分辨拒答來源。同步 SDK 以 `asyncio.to_thread` 執行。

### D4. Fail closed
Guardrail 已設定卻呼叫失敗時，寧可回傳錯誤也不跳過，避免攻擊者製造錯誤來繞過檢查。只有「完全沒設定」（本機開發）才跳過並警告。

### D5. Guardrail 用 Terraform 管理
拒絕話題與強度是安全設定，需要版本控制與 review。Terraform 從這個 ticket 開始存在，ticket 13 再加入部署資源。

### D6. Guardrail 使用 Standard 方案
Classic 方案只支援英文、法文、西班牙文，中文的 prompt injection 可能偵測不到。內容過濾（含 prompt attack）與拒絕話題都設定 `tier_name = "STANDARD"`；Standard 方案必須搭配 cross-region 設定（`us.guardrail.v1:0` guardrail profile）。驗收時以中文的 prompt injection 實測。

### D7. 不能用空結果敷衍
ticket 2 實測發現，模型遇到刪除資料、讀取系統表這類要求時，會產生必定查不到資料的 SQL（`WHERE FALSE`、`WHERE 1 = 0`、`LIMIT 0`），畫面只顯示「查無資料」，使用者不知道其實是被拒絕了。system prompt 明確規定這類情況要回 `refuse`。不在 SQL 防護中偵測恆假條件：正常查詢也可能出現，誤擋的代價比較高；改由 ticket 5 的評估統計。

### D8. 回應合約
- 新增 `refusal_source`：`input_guardrail`、`model`，其餘情況為 `null`。
- `refused`、`clarify` 一律回 HTTP 200，`sql=null`、`columns=[]`、`rows=[]`、`error_kind=null`。
- 產生 SQL 的介面從回傳字串改成回傳三種結果之一，類型與欄位的一致性由解析回覆時檢查。
- Guardrail 呼叫失敗回 HTTP 502、「輸入檢查暫時無法使用，請稍後再試」，與 Bedrock 模型失敗的訊息分開。

### D9. Terraform state 與權限
state 留在本機並加入 `.gitignore`（含帳號 ID 等資訊）。`terraform apply` 以使用者自己的管理員 profile 執行；API 使用的 `brewql` IAM user 只增加 `bedrock:ApplyGuardrail` 權限。CI 每個 PR 都執行 `terraform fmt -check` 與 `terraform validate`（`init -backend=false`），不需要 AWS 憑證，也不加路徑條件，避免必要檢查被跳過而卡住 PR。

## Risks / Trade-offs

- [Guardrail 誤擋正常的數據問題] → 評估（ticket 5）會統計拒答題以外被拒答的題數，必要時調整話題定義
- [本機開發忘了設定 Guardrail 而沒發現] → 啟動警告；README 說明
- [多一次 API 呼叫增加延遲] → Guardrail 通常為數百毫秒，記錄在呼叫 log
- [Standard 方案仍漏掉某些中文攻擊] → SQL 產生模型與 SQL 防護仍會擋下；端到端驗證記錄實測結果
