## ADDED Requirements

### Requirement: 真實店家資料集模式
系統 SHALL 支援 `DATASET=real` 模式，從本機匯出檔匯入真實店家的公開欄位。匯入 MUST NOT 包含任何會員或行為資料；行為資料 SHALL 以模擬方式依真實店家重新產生。預設模式 MUST 為 `demo`。

#### Scenario: 匯入真實店家
- **WHEN** 以 `DATASET=real` 與 Find Coffee 店家匯出檔啟動
- **THEN** `cafes` 為真實店家，且資料庫中沒有任何真實使用者資料

#### Scenario: 未指定模式
- **WHEN** 未設定 `DATASET`
- **THEN** 使用模擬資料集

### Requirement: 評估固定使用模擬資料
golden set 評估與 CI MUST 只在模擬資料集上執行，確保標準答案可重現。

#### Scenario: CI 執行評估
- **WHEN** CI 執行評估
- **THEN** 資料庫為模擬資料集

### Requirement: 真實資料不進版本控制
匯入檔與真實店家資料 MUST NOT 被 commit 到 repo。

#### Scenario: 誤加匯入檔
- **WHEN** 匯入檔位於 `db/import/` 下並執行 `git status`
- **THEN** 該檔案被 `.gitignore` 忽略
