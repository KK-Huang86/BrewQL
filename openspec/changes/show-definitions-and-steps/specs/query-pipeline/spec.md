## ADDED Requirements

### Requirement: 步驟事件
流程 SHALL 在每個步驟開始與結束時發出事件，步驟包含：`retrieve`、`generate`、`validate`、`execute`；重試時 SHALL 以新的嘗試編號再次發出 `generate`、`validate`、`execute`。每個事件含步驟名稱、狀態（started / succeeded / failed）、嘗試編號與簡短說明。不需要步驟事件的呼叫端（例如評估）SHALL 能不接收事件且行為不變。

#### Scenario: 一次成功
- **WHEN** 問題一次就成功
- **THEN** 依序發出四個步驟的 started 與 succeeded 事件

#### Scenario: 重試
- **WHEN** 第一次 SQL 被防護拒絕
- **THEN** 發出 `validate` failed（含原因），接著發出嘗試編號 2 的 `generate` started

### Requirement: 可取消
處理中的問題被取消時，流程 SHALL 停止後續步驟，MUST NOT 再呼叫模型或執行新的查詢。

#### Scenario: 產生 SQL 時取消
- **WHEN** 在 `generate` 步驟進行中取消
- **THEN** 不會進入 `execute`，資料庫未收到查詢
