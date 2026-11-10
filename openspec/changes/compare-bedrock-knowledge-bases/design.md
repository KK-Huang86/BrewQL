## Context

動機見 proposal.md。此時 `rag-knowledge-base` 已完成：知識文件、pgvector 匯入與檢索、static／rag 評估比較。

## Goals / Non-Goals

**Goals:** 以實測數據回答「為什麼不用 Bedrock Knowledge Bases」；比較公平、可重現；實驗資源不留下持續費用。

**Non-Goals:** 正式環境改用 Knowledge Bases、部署 Knowledge Bases、實測監控／部署／流程編排的託管方案（只做文件比較）。

## Decisions

### D1. 檢索器介面，pgvector 與 Knowledge Bases 為兩個實作
介面：輸入問題，輸出三類知識各前 N 筆，每筆含知識文件 ID 與類型。正式流程用 pgvector 實作；Knowledge Bases 實作呼叫 `Retrieve` API，以文件 metadata（ID、類型）對回 repo 中的知識文件。評估切換檢索器即可跑完整測試集，不需另寫一套流程。

### D2. Knowledge Bases 是實驗，不是正式路徑
- 資源以 Terraform 建立（與 `guardrail.tf` 同一處，單一檔案），由使用者以 deployer profile apply，比較完 destroy；不進入 `deploy-public-demo`。
- 資料來源：同一批 repo 文件上傳到 S3，每份一個檔案並附 metadata，關閉切塊，讓兩邊比較的單位相同。
- 向量儲存：實作前查證當時可用選項的計費（例如 S3 Vectors、Aurora Serverless pgvector、OpenSearch Serverless），選無最低月費或最低者；查證結果與來源記入取捨文件。
- Embedding 同樣用 Titan Text Embeddings V2（1024 維），差異只來自檢索服務本身。

### D3. 測試不呼叫 AWS
Knowledge Bases 檢索器以假的 client 測 metadata 對應、三類分流與錯誤處理；只有比較任務（4.2）呼叫真實服務。

### D4. 取捨文件記錄「選擇」與「依據」
`docs/aws-managed-alternatives.md` 每個元件一節：自建方案、對應的 AWS 託管方案、成本、維運、可攜性、本專案的選擇與理由。向量檢索一節使用實測數據；其他元件（Grafana Cloud 與 CloudWatch／Bedrock invocation logging、EC2 docker compose 與 ECS Fargate／RDS、LangGraph 與 Bedrock Agents）引用官方文件與定價頁，標註查證日期。

## Risks / Trade-offs

- [實驗資源忘記銷毀而持續計費] → 資源集中在單一檔案並加 `brewql-experiment` 標籤；destroy 任務的完成條件是 AWS 上查不到資源
- [兩邊切塊或 metadata 不同造成比較不公平] → 關閉切塊、同一 embedding 模型、同一 top-N；無法排除的差異寫入報告
- [Knowledge Bases 三類分流] → 以 metadata 篩選各查一次，或一次取較多再分流；實作時依 `Retrieve` API 支援的篩選方式決定並記錄
