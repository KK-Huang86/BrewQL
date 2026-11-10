## 1. 前置確認

- [ ] 1.1 記錄資料來源授權（Google Places 條款、Cafe Nomad 查無正式條款）與匯入、不匯入的欄位；驗證：design D4、D11 與 README 草稿一致

## 2. 清理與比對（純函式）

- [ ] 2.1 測試 + 實作：地址解析城市與行政區（臺→台、無法解析回傳 None）；驗證：測試由紅轉綠
- [ ] 2.2 測試 + 實作：無法解析時以 1 公里內最近的已解析店家補上；驗證：測試由紅轉綠
- [ ] 2.3 測試 + 實作：店家欄位白名單、NULL 字串轉換、投票排除 user 來源；驗證：測試由紅轉綠，輸出不含 `user_id`、`favorite_count`
- [ ] 2.4 測試 + 實作：Cafe Nomad 以 50 公尺＋店名比對，一家店只對一筆，評分 0 轉 NULL；驗證：測試由紅轉綠

## 3. 匯入與資料集模式

- [ ] 3.1 schema：`pet_friendly`、`has_pet` 可為 NULL，`schema.yaml` 同步；驗證：demo 重建後評估參考 SQL 試跑（`--dry-run`）結果不變
- [ ] 3.2 測試 + 實作：匯入腳本在一個交易內寫入，demo 模式與已有資料時略過，失敗 rollback；驗證：整合測試由紅轉綠
- [ ] 3.3 `db/seed/real_behavior.sql`：依真實店家產生模擬行為，計數等於明細；驗證：`db/checks` 在 real 資料庫通過
- [ ] 3.4 compose：`DATASET`、各自的 volume、`cafe-import` 服務（`REAL_DATA_DIR` 唯讀掛載）；`.gitignore` 加 `db/import/`；`.env.example` 同步；驗證：兩種模式都能啟動，`git status` 看不到匯入檔
- [ ] 3.5 測試 + 實作：評估遇到非 demo 店家時在付費呼叫前報錯停止；驗證：測試由紅轉綠

## 4. 驗證與文件

- [ ] 4.1 實際以 real 模式啟動並提問；驗證：匯入報告的筆數記入本檔，3 個問題的回答與 SQL 抽查合理
- [ ] 4.2 README：兩種模式、切換方式、資料來源與授權限制；驗證：照 README 從 demo 切到 real 再切回 demo 成功
