## Purpose

把營運人員的中文問題轉換成 SQL 並執行，回傳可供畫面呈現的結果，是 GenBI 所有功能的核心路徑。

## ADDED Requirements

### Requirement: 問題轉 SQL 並執行
系統 SHALL 將中文問題連同資料表說明送給 Bedrock 上的 Claude 產生 SQL，經 `sql-guardrails` 驗證後執行，並回傳 `status=ok`、實際執行的 SQL、欄位名稱與資料列。模型 ID SHALL 由設定決定（預設 Claude Haiku 5.5）。

#### Scenario: 簡單問題
- **WHEN** 問題為「台北市有幾家咖啡店？」
- **THEN** 回傳 `status=ok`，SQL 查詢 `cafes`，結果為台北市的咖啡店數量

#### Scenario: 切換模型
- **WHEN** 設定的模型 ID 改為其他 Claude 模型
- **THEN** 不需修改程式碼即使用該模型

### Requirement: 結構化輸出
系統 SHALL 要求模型以符合 JSON schema 的結構化格式回覆，至少包含 `sql` 欄位。回覆不符合 schema、`sql` 為空白、或回覆因長度上限被截斷時，MUST 回傳 `status=error` 與說明，MUST NOT 崩潰，也 MUST NOT 執行任何查詢。

#### Scenario: 合法的結構化回覆
- **WHEN** 模型回覆 `{"sql": "SELECT COUNT(*) FROM cafes"}`
- **THEN** 使用該 SQL 進入防護與執行

#### Scenario: sql 為空白
- **WHEN** 模型回覆 `{"sql": "  "}`
- **THEN** 回傳 `status=error`，沒有執行任何查詢

#### Scenario: 回覆被截斷
- **WHEN** 模型回覆的結束原因為達到 token 上限
- **THEN** 回傳 `status=error`，沒有執行任何查詢

### Requirement: 輸入驗證與服務錯誤
問題去除前後空白後 MUST 為 1~1000 字元，否則不呼叫模型。Bedrock 的網路、權限、限流錯誤 MUST 被記錄並往外拋出，MUST NOT 被當作正常結果或靜默忽略。

#### Scenario: 空白問題
- **WHEN** 問題只有空白
- **THEN** 回報輸入錯誤，不呼叫模型

#### Scenario: Bedrock 權限不足
- **WHEN** AWS 憑證沒有呼叫模型的權限
- **THEN** 錯誤被記錄並往外拋出

### Requirement: 呼叫紀錄
每次模型呼叫 SHALL 記錄模型 ID、輸入 token、輸出 token 與結束原因。

#### Scenario: 留下紀錄
- **WHEN** 完成一次模型呼叫
- **THEN** log 中有模型 ID、token 數與結束原因

### Requirement: 不阻塞事件迴圈
模型呼叫 MUST NOT 阻塞 async 事件迴圈；呼叫進行中，其他請求 SHALL 能正常回應。

#### Scenario: 呼叫期間健康檢查
- **WHEN** 模型呼叫進行中時呼叫健康檢查
- **THEN** 健康檢查立即回應
