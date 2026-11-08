# BrewQL - Find Coffee 營運數據助理

## 專案概述

BrewQL 是一個 GenBI（生成式 BI）服務：讓不會寫 SQL 的營運人員用中文提問，系統產生 SQL、經多層防護後執行，回傳圖表與答案，並附上實際執行的 SQL 讓使用者檢視與修改。資料來源為 Find Coffee（咖啡店搜尋服務）的資料表結構加上模擬的使用者行為資料；BrewQL 是 Find Coffee 旁的獨立服務，只能唯讀存取資料，不修改 Find Coffee 本身。

## 技術棧

- **後端**: FastAPI（全面 async）+ Python >= 3.13
- **LLM**: Amazon Bedrock 上的 Claude（預設 Haiku 5.5），透過 `anthropic[bedrock]` SDK 呼叫，使用 structured outputs
- **輸入防護**: Amazon Bedrock Guardrails
- **流程編排**: 一般 async 函式起步，步驟與分支變多後改用 LangGraph
- **RAG**: Bedrock Titan Text Embeddings + pgvector
- **SQL 解析與驗證**: sqlglot
- **資料庫**: PostgreSQL 16 + pgvector，asyncpg 連線
- **前端**: React + TypeScript + Vite，圖表使用 Recharts
- **容器化**: Docker Compose
- **IaC**: Terraform（AWS：EC2、IAM、Budgets）
- **套件管理**: uv（後端）、npm（前端）
- **測試與品質**: pytest、pytest-asyncio、Ruff；Vitest、React Testing Library
- **Spec 工作流**: OpenSpec + Spectra

## 專案結構（monorepo）

```
├── backend/            # FastAPI 服務
│   ├── app/           # API、SQL 產生、SQL 防護、圖表選擇、資料庫執行器
│   ├── scripts/       # smoke 腳本（實際呼叫 Bedrock）
│   └── tests/         # 單元測試；integration/ 為需要真實 Postgres 的整合測試
├── frontend/           # React 前端
├── db/
│   ├── init/          # Postgres 首次啟動執行：schema、view、模擬資料、唯讀角色
│   └── checks/        # 驗證模擬資料故事的 SQL
├── infra/terraform/    # AWS 部署資源
├── openspec/           # 規格、change proposal、design 與 tasks
├── .github/workflows/  # CI（每個 PR 都跑；push 到 develop/main 才依目錄 path filter）
└── docker-compose.yml  # db、backend、frontend
```

目錄會隨 OpenSpec change 逐步建立；尚未完成的 change 對應的目錄可能還不存在。

## 開發指令

```bash
# 後端：安裝依賴、測試、靜態檢查
uv --directory backend sync --group dev
uv --directory backend run pytest -q
uv --directory backend run ruff check .

# commit 前檢查（每個 clone 安裝一次）
uvx pre-commit install

# 整合測試用 Postgres（CI 同一組測試密碼；用完 down）
eval "$(db/test-db.sh up)"; uv --directory backend run pytest -q; db/test-db.sh down

# 實際呼叫 Bedrock 的 smoke 測試（需要 AWS 憑證與模型權限）
uv --directory backend run python -m scripts.ask "台北市有幾家工作友善的咖啡店？"

# 前端
npm --prefix frontend install
npm --prefix frontend test
npm --prefix frontend run build

# 完整容器化環境（重建 Demo 資料庫：docker compose down -v）
docker compose up --build

# OpenSpec change 驗證
openspec validate <change-name> --strict

# Terraform
terraform -chdir=infra/terraform fmt -check
terraform -chdir=infra/terraform validate
terraform -chdir=infra/terraform plan
```

## 注意事項

- Commit 訊息一律使用英文，格式為 Conventional Commits（`feat:`、`fix:`、`chore:`、`docs:`、`test:`、`refactor:`），例如 `feat: add read-only query executor`。OpenSpec 文件與程式碼註解不受此限。
- 分支策略：`main` 為可 Demo／部署的穩定版本，`develop` 為開發主線，兩者在 GitHub 上受保護，只能透過 PR 合併（禁止直接 push、force push 與刪除）。每個 OpenSpec change 從 `develop` 開 `feature/<change-name>` 分支，以 PR 合回 `develop`；要部署時再從 `develop` 開 PR 合進 `main`。
- PR 標題使用英文（Conventional Commits 格式，例如 `feat: answer the first question end to end`），PR 內容使用繁體中文。撰寫 PR 內容時，必須先用 Skill tool 呼叫 `mattpocock-skills:pr`，依其範本（Summary、Evidence、Merge Danger）撰寫。
- 每完成兩個 OpenSpec change（PR 合併並 archive 後），提醒使用者執行 `/mattpocock-skills:retro`（此 skill 只能由使用者觸發），並依 retro 結果向使用者說明執行層面可優化之處。
- 環境變數放在 `.env`；不得 commit secrets，新增變數時同步更新 `.env.example`。
- API 連線資料庫一律使用唯讀角色 `genbi_reader`，不得使用資料庫擁有者帳號。
- LLM 產生或使用者提供的 SQL 必須經過 SQL 防護驗證才能執行；不得新增繞過防護的執行路徑。
- 不得把真實 Find Coffee 使用者資料（LINE ID、收藏紀錄等）放進 repo 或 Demo 資料庫。
- Unit test 不得真實呼叫 Bedrock 或其他外部服務；需要真實 Postgres 的測試放在 `backend/tests/integration/`。
- 部署主機以 IAM role 取得 AWS 臨時憑證，不得建立或使用長期 access key。

# TDD 開發規範（專案固定規則）

任何實作階段（尤其 `/spectra-apply` 或直接寫程式碼）都必須遵守：

1. **先寫測試，後寫程式碼**：在生成/修改任何實作程式碼之前，必須先為該功能撰寫對應的 unit test。若某個任務沒有對應的 unit test，禁止生成該任務的實作程式碼。
2. **邊界案例優先**：撰寫 unit test 時，除了基本 happy path，必須額外涵蓋邊界情況（空值、極端值、錯誤輸入、併發/重複呼叫等），確保測試案例能反映真實使用情境與潛在風險。
3. **分階段驗證**：每個開發階段完成後都要驗證再往下走，而不是一次做完才驗證，包含（但不限於）：
   - 測試案例本身是否合理覆蓋需求與邊界情況
   - 新寫的測試在無實作前應為紅燈（fail）
   - 實作完成後測試需全部通過（green）
   - 通過後再視情況重構（refactor），且重構後測試仍需全綠
   - git 歷史要能證明順序：每個循環先 commit 紅燈測試（`test: ... (red)`），再 commit 實作（`feat: ... (green)`）；測試一寫就綠的驗證型測試，以 `test:` 單獨 commit 並在訊息中說明突變驗證
4. **測試全過才能生成/合併程式碼**：只有當對應的 unit test（含邊界案例）全部撰寫完成且驗證通過後，才可以生成或提交最終的實作程式碼。
5. **測試不可為了遷就程式碼而修改**：unit test 撰寫完成後，除非商業邏輯（需求本身）有變更，否則不可以因為程式碼實作結果、或是為了讓測試通過，而回頭修改測試內容（例如放寬斷言、刪除邊界案例、改動期望值以符合實作輸出）。測試失敗時，預設應該修的是程式碼，而不是測試；只有在確認是商業邏輯變更時，才能連動修改測試，且需同步說明變更原因。

# 資料操作穩健性規範（專案固定規則）

涉及資料寫入/狀態變更的開發，必須考慮以下事項：

1. **重視邊界情況**：實作前先想清楚輸入的邊界（空值、極端值、型別錯誤、超量資料等），並反映在程式邏輯與測試中。
2. **原子性操作**：提交相關聯的多筆資料變更時，要嘛全部成功、要嘛全部不生效，不可只完成一半。單一資料庫內優先用 transaction；跨系統/跨服務無法用單一 transaction 涵蓋時，需設計補償機制（compensating action / saga），不能假裝有原子性。
3. **失敗時要能 rollback**：任何寫入流程都要事先設計失敗後的回復路徑，不能只處理成功路徑（happy path）。
4. **冪等性（Idempotency）**：同一操作重複執行（重試、重複請求）結果需與只執行一次相同，避免重複扣款、重複寫入等副作用，這點在搭配 retry/rollback 機制時尤其重要。
5. **錯誤不可被吞掉**：例外必須明確拋出或記錄，禁止 catch 後靜默忽略；rollback 觸發原因也需可被追蹤。
6. **併發安全**：多請求同時操作同一資料時，需考慮鎖定或版本控制（如 optimistic lock），避免競爭條件造成資料不一致。
7. **逾時與重試需有上限**：避免無限重試造成連鎖失敗或重複副作用，並應與冪等性設計搭配。
8. **可觀測性**：失敗、rollback、重試都要有 log／監控可查，方便事後追查根因。

# PR 前的 Spec 一致性檢查（專案固定規則）

程式碼與 spec/proposal/design 是否一致，分兩層把關，性質不同：

1. **結構檢查（交給 CI）**：若這次變更修改了實作程式碼，卻沒有同步修改對應的 `openspec/specs/**` 或該 change 目錄下的文件，CI 應直接擋下 PR。這是可自動化、確定性的規則，不需要 AI 判斷。
2. **語意檢查（由我在流程中執行，不寫進 CI）**：驗證 task/實作是否真的符合 proposal、design 的描述，需要語意判讀，不適合當 CI 硬性 gate（成本高、可能不穩定）。因此：
   - change 的任務完成、要準備開 PR 之前，依序執行：`openspec validate <change> --strict`、`spectra drift <change>`（檢查 spec 與程式碼現狀的落差）、`mattpocock-skills:code-review`（Standards 與 Spec 兩個面向，以 `develop` 為比較基準）。
   - 任一項回報落差，必須先處理（修正實作或回頭調整 spec／design／tasks），確認一致後才能建議使用者開 PR。
   - 這一層是流程約定，仰賴我主動執行，不是 CI 保證；若程式碼是透過我以外的方式修改，此規則不會被觸發。
