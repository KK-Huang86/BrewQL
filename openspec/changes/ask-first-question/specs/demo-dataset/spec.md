## Purpose

提供與 Find Coffee 資料表結構一致、不含任何真實使用者資料的 Demo 資料庫，讓 GenBI 有資料可以查詢。

## ADDED Requirements

### Requirement: 一鍵建立資料庫
在空的資料 volume 上執行 `docker compose up` 時，資料庫 SHALL 自動建立 schema、唯讀角色與示範資料。缺少 `POSTGRES_PASSWORD` 或 `GENBI_READER_PASSWORD` 時 MUST 啟動失敗並指出缺少的變數。資料庫 port MUST 只綁定 127.0.0.1。

#### Scenario: 首次啟動
- **WHEN** 已設定 `.env` 並執行 `docker compose up`
- **THEN** 資料庫健康檢查通過，`cafes` 有資料

#### Scenario: 缺少密碼
- **WHEN** 未設定 `GENBI_READER_PASSWORD`
- **THEN** 啟動失敗並指出 `GENBI_READER_PASSWORD`

### Requirement: 咖啡店資料
資料庫 SHALL 包含沿用 Find Coffee 結構的 `cafes`（含 `city`、`district`、`rating`、`limited_time`、`has_socket` 等），約 200 家示範咖啡店，分布於台北市與新北市多個行政區，並使用固定亂數種子。

#### Scenario: 分布
- **WHEN** 依城市與行政區統計 `cafes`
- **THEN** 台北市與新北市都有資料，至少 8 個行政區

#### Scenario: 可重現
- **WHEN** 刪除 volume 後重建
- **THEN** 各行政區咖啡店數量與重建前相同
