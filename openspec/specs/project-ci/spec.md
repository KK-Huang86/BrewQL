# project-ci Specification

## Purpose
以自動化檢查守住程式碼品質與「程式碼和 spec 同步」的專案規則。

## Requirements

### Requirement: 後端與前端檢查
CI SHALL 在每個 PR 執行後端 lint 與測試、前端 build 與測試；任何一項失敗 MUST 讓 CI 失敗。push 到 `develop`/`main` 時才依目錄以 path filter 分開執行。

#### Scenario: 後端測試失敗
- **WHEN** PR 讓某個後端測試失敗
- **THEN** CI 失敗

### Requirement: Spec 一致性結構檢查
CI SHALL 在 PR 修改 `backend/`、`frontend/`、`db/`、`infra/` 卻沒有修改 `openspec/` 時失敗。

#### Scenario: 只改程式碼
- **WHEN** PR 只修改 `backend/app/main.py`
- **THEN** spec 檢查失敗

#### Scenario: 程式碼與 spec 一起改
- **WHEN** PR 同時修改 `backend/` 與 `openspec/changes/...`
- **THEN** spec 檢查通過
