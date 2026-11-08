## ADDED Requirements

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
