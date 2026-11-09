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
uv --directory backend run pytest -q        # 指定檔案時路徑相對 backend/，例如 tests/test_charts.py
uv --directory backend run ruff check .

# commit 前檢查（每個 clone 安裝一次）
uvx pre-commit install

# 整合測試用 Postgres（CI 同一組測試密碼；用完 down）
eval "$(db/test-db.sh up)"; uv --directory backend run pytest -q; db/test-db.sh down

# 模擬資料故事檢查（db/checks，每個檔案失敗時 RAISE）
PSQL="docker exec -i brewql-test-db psql -U genbi_owner -d genbi" db/checks/run.sh
# 證明檢查會失敗：在交易中改資料、跑一個檢查、一定 rollback（caught 才算有效）
PSQL="..." db/checks/mutate.sh "UPDATE cafes SET favorite_count = favorite_count + 1 WHERE id = 1" 08_views_favorites.sql

# 實際呼叫 Bedrock 的 smoke 測試（需要 AWS 憑證與模型權限）
uv --directory backend run python -m scripts.ask "台北市有幾家工作友善的咖啡店？"

# 評估黃金測試集（先 --dry-run 免費檢查；完整執行會呼叫 Bedrock，結果摘要記入 backend/evaluation/RESULTS.md）
AWS_PROFILE=brewql uv --directory backend run python -m evaluation [--dry-run] [--only q01,q12]
# 對測試資料庫試跑參考 SQL（DB_PORT 要和 DATABASE_URL 的 port 一致）
DB_PORT=5499 DATABASE_URL=postgresql://genbi_reader:ci-reader-password@127.0.0.1:5499/genbi \
  uv --directory backend run python -m evaluation --dry-run

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

- **寫測試、新增資料寫入路徑、準備開 PR 前，先讀 `CODING_STANDARDS.md`**（TDD、資料操作穩健性、PR 前 spec 一致性檢查）；code review 依該檔審查。
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
