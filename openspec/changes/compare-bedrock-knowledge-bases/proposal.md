## Why

`rag-knowledge-base` 用自建的 pgvector 做檢索。AWS 上的標準做法是 Amazon Bedrock Knowledge Bases，面試或客戶一定會問「為什麼不用託管服務」。與其憑主觀判斷，不如用同一批知識文件與同一測試集實測兩邊的正確率、檢索結果、延遲與成本，並把本專案其他元件的自建與託管取捨一起寫清楚。

## What Changes

- 檢索器介面：檢索包在同一介面後，pgvector 與 Bedrock Knowledge Bases 為兩個實作，評估可指定使用哪一個
- Knowledge Bases 實驗資源：以 Terraform 建立（S3 資料來源、向量儲存、Knowledge Base、IAM role），比較完即銷毀，不進入部署
- 評估：同一測試集以兩種檢索器執行，比較正確率、每題檢索到的文件、檢索延遲與成本
- 取捨文件：`docs/aws-managed-alternatives.md` 記錄向量檢索（實測）、監控、部署、流程編排四個元件的自建與託管方案比較與選擇理由

## Capabilities

### New Capabilities

（無）

### Modified Capabilities

- `knowledge-retrieval`: 檢索透過可替換的介面提供，新增 Knowledge Bases 實作。
- `evaluation`: 支援指定檢索器並比較兩份報告的檢索差異。

## Impact

- 新增：Knowledge Bases 檢索器、`infra/terraform` 的實驗資源檔、`docs/aws-managed-alternatives.md`
- 成本：只在比較期間存在；向量儲存選無最低月費或最低者，比較完 `terraform destroy`；評估跑一次測試集的 Bedrock 費用
- 正式流程不變：預設仍為 pgvector；是否改用 Knowledge Bases 依結果另開 change
- 依賴 ticket：`rag-knowledge-base`
