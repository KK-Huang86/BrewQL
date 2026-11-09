## Why

「哪裡缺工作友善的咖啡店」是 Find Coffee 最有行動價值的洞察：某區搜尋量高、但常常搜尋不到結果，就是供給缺口。讓營運人員一句話看到依行政區比較的長條圖，並在問單一數字時看到醒目的數字卡。

## What Changes

- 模擬資料加入「供給缺口」故事：內湖區搜尋量高、但 `result_count = 0` 的比例最高
- schema 說明加入「搜尋落空率」定義
- 圖表選擇新增：文字 + 數值 → 長條圖（≤ 30 類）、單一數值 → 數字卡
- 畫面新增長條圖與數字卡
- 黃金測試集加入行政區比較題

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

- `demo-dataset`: 新增供給缺口故事。
- `result-visualization`: 新增長條圖與數字卡判斷。
- `query-web-ui`: 新增長條圖與數字卡。
- `evaluation`: 加入行政區比較題。

## Impact

- 修改：模擬資料、schema 說明、圖表選擇、前端
- 依賴 ticket：`search-trend-line-chart`
