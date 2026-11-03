## Purpose

用固定的黃金測試集量化 GenBI 的正確率、拒答能力、延遲與成本，讓每次改動都能以數據比較好壞。

## ADDED Requirements

### Requirement: 黃金測試集
測試集 SHALL 為版本控制中的資料檔，每題包含：編號、問題、難度（easy / medium / hard / refuse）、以及「參考 SQL」或「預期狀態（refused / clarify）」二擇一；可標註結果是否需比對順序。載入時題號重複、缺少必要欄位、或同時有參考 SQL 與預期狀態 MUST 報錯並停止。初始 SHALL 至少 15 題，涵蓋四種難度。

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

#### Scenario: 該反問卻回答
- **WHEN** 預期為 `clarify`，系統回傳 `ok`
- **THEN** 判為錯誤

### Requirement: 指標與報告
每次評估 SHALL 輸出：整體與各難度正確率、拒答題正確率、p50 與 p95 回應時間、每題平均 token、每題平均成本（依設定的模型單價計算）、修正次數分布，以及每題的明細（問題、對錯、系統 SQL、參考 SQL、錯誤訊息、耗時、token）。報告 SHALL 有機器可讀與人可讀兩種格式，並記錄模型 ID、設定與執行時間。

#### Scenario: 完整報告
- **WHEN** 完成一次評估
- **THEN** 產出 JSON 與 Markdown 報告，含上述所有指標與逐題明細

### Requirement: 成本控制
評估 SHALL 在開始前顯示題數與預估呼叫次數，並支援只跑部分題目與不呼叫模型的試跑（只驗證測試集與參考 SQL 可執行）。單題失敗（含服務錯誤）SHALL 記錄後繼續下一題，MUST NOT 中斷整體評估。

#### Scenario: 試跑
- **WHEN** 以試跑模式執行
- **THEN** 不呼叫模型，回報每題參考 SQL 是否可執行

#### Scenario: 單題服務錯誤
- **WHEN** 第 3 題呼叫 Bedrock 時發生服務錯誤
- **THEN** 第 3 題記為錯誤並註明原因，評估繼續執行第 4 題
