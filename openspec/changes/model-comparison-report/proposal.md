## Why

很多人只會說「正確率 85%」，能說出「剩下 15% 錯在哪、為什麼、怎麼改」以及「Haiku 和 Sonnet 在正確率與成本上怎麼取捨」的人很少。這份報告是面試時直接展示的成果，呼應 Going Cloud 重視的 LLM 評估與 FinOps。

## What Changes

- 評估支援指定模型，比較 Claude Haiku 5.5 與 Claude Sonnet 5.5（皆為 RAG 模式）
- 錯誤分類：每道答錯的題目標註錯誤類型（欄位選錯、名詞理解錯、JOIN 錯誤、時間範圍錯誤、該反問卻回答、其他）
- 依錯誤分析做至少一輪改善（補知識文件或調整 prompt），並重新評估
- 成本優化：啟用 prompt caching（固定的 system prompt 放在可快取的前綴），量測快取命中 token 與每題成本的變化
- 產出一頁評估報告，放進版本控制並從 README 連結

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

- `evaluation`: 新增模型比較、錯誤分類與評估報告。

## Impact

- 修改：評估程式、知識文件或 prompt（依分析結果）
- 新增：評估報告文件、錯誤標註檔
- 成本：Sonnet 每次完整評估約數十美分；預計共執行 4～6 次
- 依賴 ticket：`rag-knowledge-base`
