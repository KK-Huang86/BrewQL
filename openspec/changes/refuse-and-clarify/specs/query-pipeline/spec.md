## ADDED Requirements

### Requirement: 三種結果的結構化輸出
結構化輸出的 schema SHALL 擴充為三種結果之一：`sql`（附 SQL）、`refuse`（附原因）、`clarify`（附反問）。結果類型與對應欄位不一致時（例如類型為 `sql` 但 SQL 空白、類型為 `refuse` 但原因空白）MUST 回傳 `status=error`，MUST NOT 執行任何查詢。

#### Scenario: 類型與內容不一致
- **WHEN** 模型回覆類型為 `refuse` 但原因為空白
- **THEN** 回傳 `status=error`，沒有執行任何查詢

### Requirement: 拒答
當問題要求修改資料、與數據分析無關、或要求預測未來時，系統 SHALL 回傳 `status=refused`、原因，以及 `refusal_source=model`，MUST NOT 執行任何 SQL。Bedrock 回應的結束原因為 refusal 時 SHALL 同樣視為拒答。

#### Scenario: 預測未來
- **WHEN** 問題為「下個月會有幾位新會員？」
- **THEN** 回傳 `status=refused`，說明只能查詢歷史資料，資料庫未收到查詢

#### Scenario: 模型安全拒絕
- **WHEN** Bedrock 回應的結束原因為 refusal
- **THEN** 回傳 `status=refused`，不讀取回覆內容

### Requirement: 反問
當問題缺少必要資訊（時間範圍、指標定義等）時，系統 SHALL 回傳 `status=clarify` 與反問內容，MUST NOT 執行任何 SQL。

#### Scenario: 模糊問題
- **WHEN** 問題為「最近熱門的店」
- **THEN** 回傳 `status=clarify`，反問「最近」的範圍或「熱門」的指標，資料庫未收到查詢
