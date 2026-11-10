## 1. 快照

- [x] 1.1 測試 + 實作：YouBike 裁切（台北與新北兩種欄位、去前綴、只收營運中、臺大公館校區→大安區、臺→台、未知行政區報錯、不含即時欄位）；驗證：測試由紅轉綠
  - 結果：`app/open_data.py` 的 `youbike_rows(taipei, new_taipei, districts, as_of)`，`districts` 由呼叫端以 `district_population` 的 (city, district) 傳入。9 個測試紅轉綠（紅燈原因為介面不存在），邊界含停用站、外縣市、未知行政區、重複站號、缺欄位、空輸入。座標以 `str()` 轉 `Decimal` 再取 6 位小數，避免台北 float 的二進位誤差讓重跑結果不同。以 2026-11-11 下載檔試跑：3,398 站（台北 1,803、新北 1,595），涵蓋 41 區全部，沒有未知行政區
- [x] 1.2 測試 + 實作：捷運出入口整理成車站（站名正規化含台北車站、平均座標、最近 YouBike 行政區、對照表修正）；驗證：測試由紅轉綠
  - 結果：`app/open_data.py` 的 `mrt_rows(exits, youbike, as_of, fixes=MRT_DISTRICT_FIXES)`，對照表在 1.3 抽查後填入。12 個測試紅轉綠（紅燈原因為介面不存在）。邊界含：無編號出口、台北車站、修正值指向不存在的車站、名稱格式不明、1 公里內沒有 YouBike、沒有 YouBike 資料、座標無法解析、空輸入；座標錯誤改成拋 `ValueError`，YouBike 一併適用。以真實檔試跑時遇到「南港展覽館站出口2A」停下，另以 `test:`（red）／`feat:`（green）支援字母編號（2A、1A）。真實檔：119 站、390 個出口，台北 74 站、新北 45 站，最近 YouBike 距離最遠 241m（松山機場）
- [x] 1.3 下載官方檔產生快照；抽查邊界與隨機車站行政區（D3）；驗證：站數與官方檔一致、抽查結果記錄於本任務、重跑檔案不變
  - 結果：抽查改為全部比對（D3）：以捷運官網車站頁的 API 取得 120 個車站代碼的地址（站名集合與出口檔的 119 站完全一致），最近 YouBike 法判錯 7 站，全部在台北市，填入 `MRT_DISTRICT_FIXES`（test red → feat green）；判錯原因都是車站在行政區交界，例如公館站最近的 YouBike 在臺大校區（大安區），車站地址在中正區。原本懷疑的中山站，官方地址就是大同區，最近 YouBike 法判斷正確。快照指令加入兩份 YouBike JSON、Big5 出口檔與下載日 `AS_OF`（test red → feat green）；快照 fixture 原本只有一站，觸發「對照表的車站不在檔案中」檢查，另以 `test:` commit 補齊 7 個車站。產生快照：`district_population=41 universities=49 youbike_stations=3398 mrt_stations=119`，既有兩個快照不變；以相同下載檔與日期重跑，4 個檔案的 shasum 相同；快照的 119 站與官方地址重新比對，0 站不一致。`youbike_stations.csv` 約 296 KB

## 2. 載入與防護

- [ ] 2.1 `01_schema.sql` 新增兩張表、`06_open_data.sh` 載入並授權；驗證：整合測試以 `genbi_reader` 查得到兩張表
- [ ] 2.2 測試 + 實作：SQL 白名單加入兩張表；驗證：測試由紅轉綠
- [ ] 2.3 `09_open_data_join.sql` 加入兩張表；驗證：demo 通過，mutation 改壞一站行政區時失敗

## 3. 模型與評估

- [ ] 3.1 知識文件與 `STATIC_KNOWLEDGE`：兩張表、「交通便利度」名詞；驗證：知識文件測試通過
- [ ] 3.2 golden set 新增 2 題交通題目；驗證：`--dry-run` 全部 ok
- [ ] 3.3 static 與 rag 各跑 2 次評估；驗證：結果與 token 變化記入 `RESULTS.md`

## 4. 文件

- [ ] 4.1 README：兩份資料的來源、下載日、授權、重產方式；real 模式實際提問 1 題交通問題；驗證：照 README 重產快照檔案不變
