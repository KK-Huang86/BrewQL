## Context

動機見 proposal.md。此時已有 demo／real 兩個資料集（`import-real-cafes`）、RAG 知識文件（`rag-knowledge-base`）與 26 題評估基準。

## Goals / Non-Goals

**Goals:** 兩份公開資料以行政區串到既有資料；快照可重現；新表一樣受 SQL 防護；評估量化跨來源題目的正確率。

**Non-Goals:** 距離計算、即時 API、PostGIS、行政區界。

## Decisions

### D1. 快照進 repo，由腳本產生
官方檔（政府資料開放授權，可散布）下載後，以 `backend/scripts/prepare_open_data.py` 裁成快照：只留需要的欄位、只收台北市與新北市、城市寫法統一為「台」。快照放 `db/init/open_data/`，連同來源網址與版本寫在檔頭註解之外的 README 表格。腳本可重跑，產生的檔案相同；官方更新時換來源檔重跑即可。

裁切規則寫成純函式並以單元測試驗證，官方檔不進 repo（只在本機下載）。

### D2. 不收個人資訊
大專校院名錄含校長職稱與姓名、電話傳真；這些對分析沒有用，快照只留學校代碼、名稱、公私立、體制、城市、行政區。

### D3. 資料表
```sql
district_population (city, district, population, area_km2, as_of)   -- PRIMARY KEY (city, district)
universities (code, name, ownership, level, city, district)          -- PRIMARY KEY (code)
```
`as_of` 記錄資料時間（例如 `2025-12-31`），模型與 README 都能說明「人口是 114 年底」。`ownership` 為「公立／私立」，`level` 為官方的體制欄位原值。

### D4. 載入與權限
`db/init/06_open_data.sh` 在兩種資料集都執行（公開資料與店家來源無關），以 `\copy` 載入快照並 GRANT SELECT 給 `genbi_reader`。與 demo seed 相同，快照放在 init 目錄的子資料夾，Postgres 不會直接執行。CI 與測試資料庫跑同一支腳本。

### D5. 串接檢查
`db/checks` 新增一個檢查：demo 的每個行政區都對得到人口資料，`universities` 的行政區都在 `district_population` 裡。行政區名稱不一致時檢查失敗，而不是查詢時悄悄少算。

### D6. 讓模型會用
- 知識文件：兩張表的 schema；名詞「每萬人咖啡店數」＝店家數 ÷ 人口 × 10,000；範例一題（新北市每萬人咖啡店數；rag-knowledge-base 限定範例 10 到 15 題，現有 14 題，行政區排行的寫法放在名詞定義）。`STATIC_KNOWLEDGE` 同步。
- 知識文件寫「以 district 串接」：台北市與新北市沒有同名行政區。第一版寫「以 city + district 串接」時，rag 把城市也當分組條件，q08、q19 退步（見 RESULTS.md）。
- SQL 白名單加入兩張表。
- golden set 新增 3 題跨來源題目（含 1 題 hard），以 demo 資料計算標準答案；static 與 rag 各跑 2 次，記入 `RESULTS.md`。

## Risks / Trade-offs

- [大專校院資料停在 108 學年度] → README 與 `as_of` 標明年度；只用於行政區層級的比較
- [行政區名稱不一致造成 join 遺漏] → 快照統一寫法，D5 的檢查在 CI 擋下
- [新表讓 static prompt 變長] → 這正是 RAG 的用途；評估記錄 token 變化
- [real 資料集有 demo 沒有的行政區] → 兩城市 41 區全收，real 的行政區都對得到
