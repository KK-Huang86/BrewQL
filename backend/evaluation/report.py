"""Evaluation reports: JSON for tools and later comparison, Markdown for reading and error analysis."""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from evaluation.metrics import QuestionOutcome, Summary


@dataclass(frozen=True)
class RunInfo:
    started_at: datetime
    model_id: str
    # "<id>:<version>", or None when the run skipped the input guardrail.
    guardrail: str | None
    max_sql_retries: int
    golden_file: str


def to_json(info: RunInfo, summary: Summary, outcomes: list[QuestionOutcome]) -> dict[str, Any]:
    run = asdict(info)
    run["started_at"] = info.started_at.isoformat()
    summary_data = asdict(summary)
    for difficulty, score in summary.by_difficulty.items():
        summary_data["by_difficulty"][difficulty]["accuracy"] = score.accuracy
    return {"run": run, "summary": summary_data, "questions": [_detail(o) for o in outcomes]}


def _detail(o: QuestionOutcome) -> dict[str, Any]:
    u = o.usage
    return {
        "id": o.question.id,
        "difficulty": o.question.difficulty,
        "question": o.question.question,
        "correct": o.correct,
        "reason": o.reason,
        "status": o.status,
        "refusal_source": o.refusal_source,
        "attempts": o.attempts,
        "sql": o.sql,
        "reference_sql": o.question.sql,
        "expect": o.question.expect,
        "elapsed_ms": u.elapsed_ms if u else None,
        "input_tokens": u.input_tokens if u else None,
        "output_tokens": u.output_tokens if u else None,
        "guardrail_topic_units": u.guardrail.topic_units if u else None,
        "guardrail_content_units": u.guardrail.content_units if u else None,
        "cost_usd": o.cost_usd,
        "error": o.error,
    }


def to_markdown(info: RunInfo, summary: Summary, outcomes: list[QuestionOutcome]) -> str:
    cost_note = "" if summary.cost_complete else "（不完整：有模型不在價目表）"
    lines = [
        f"# 評估報告 {info.started_at.isoformat()}",
        "",
        f"- 模型：`{info.model_id}`",
        f"- 輸入 Guardrail：`{info.guardrail or '未啟用'}`",
        f"- MAX_SQL_RETRIES：{info.max_sql_retries}",
        f"- 測試集：`{info.golden_file}`",
        "",
        "## 指標",
        "",
        "| 指標 | 數值 |",
        "|---|---|",
        f"| 正確率 | {summary.correct}/{summary.total}（{_pct(summary.accuracy)}） |",
        f"| 拒答／反問題正確率 | {_pct(summary.refusal_accuracy)} |",
        f"| 誤擋（該回答卻拒答或反問） | {summary.false_refusals} |",
        f"| 服務錯誤 | {summary.service_errors} |",
        f"| p50／p95 回應時間 | {_ms(summary.p50_ms)}／{_ms(summary.p95_ms)} |",
        f"| 每題平均 token（輸入／輸出） | {_num(summary.avg_input_tokens)}／{_num(summary.avg_output_tokens)} |",
        f"| 每題平均成本 | {_usd(summary.avg_cost_usd)}{cost_note} |",
        f"| 總成本 | {_usd(summary.total_cost_usd)}{cost_note} |",
        f"| 嘗試次數分布 | {_attempts(summary.attempts)} |",
        "",
        "| 難度 | 正確 | 正確率 |",
        "|---|---|---|",
        *(f"| {d} | {s.correct}/{s.total} | {_pct(s.accuracy)} |" for d, s in summary.by_difficulty.items()),
        "",
        "比對方式：比較查詢結果而非 SQL 字串；忽略欄位名稱與順序，數值四捨五入到小數 2 位，"
        "未標註 ordered 的題目忽略列順序。",
        "",
    ]
    # Mistakes first: they are what the report is read for.
    ordered = [o for o in outcomes if not o.correct] + [o for o in outcomes if o.correct]
    lines += [
        "## 逐題明細",
        "",
        "| 題號 | 難度 | 結果 | 狀態 | 嘗試 | 耗時 | token | 成本 | 說明 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for o in ordered:
        status = o.status or "—"
        if o.refusal_source:
            status += f"（{o.refusal_source}）"
        u = o.usage
        tokens = f"{u.input_tokens}/{u.output_tokens}" if u else "—"
        note = (o.error or o.reason or "").replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| {o.question.id} | {o.question.difficulty} | {'✅' if o.correct else '❌'} | {status} | {o.attempts} "
            f"| {_ms(u.elapsed_ms if u else None)} | {tokens} | {_usd(o.cost_usd)} | {note} |"
        )
    wrong = [o for o in ordered if not o.correct]
    if wrong:
        lines += ["", "## 答錯的題目", ""]
        for o in wrong:
            lines += [f"### {o.question.id}：{o.question.question}", ""]
            if o.question.expect:
                lines.append(f"- 預期狀態：{o.question.expect}；實際：{o.status or '—'}")
            if o.error:
                lines.append(f"- 錯誤：{o.error}")
            if o.sql:
                lines += ["", "系統 SQL：", "", "```sql", o.sql, "```"]
            if o.question.sql:
                lines += ["", "參考 SQL：", "", "```sql", o.question.sql, "```"]
            lines.append("")
    return "\n".join(lines) + "\n"


def write_reports(
    directory: Path, info: RunInfo, summary: Summary, outcomes: list[QuestionOutcome]
) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    stem = info.started_at.strftime("%Y-%m-%dT%H-%M-%SZ")
    json_path, md_path = directory / f"{stem}.json", directory / f"{stem}.md"
    json_path.write_text(json.dumps(to_json(info, summary, outcomes), ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(to_markdown(info, summary, outcomes), encoding="utf-8")
    return json_path, md_path


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value:.0%}"


def _ms(value: int | None) -> str:
    return "—" if value is None else f"{value} ms"


def _num(value: float | None) -> str:
    return "—" if value is None else f"{value:.0f}"


def _usd(value: float | None) -> str:
    return "—" if value is None else f"${value:.4f}"


def _attempts(distribution: dict[int, int]) -> str:
    return "、".join(f"{k} 次：{v} 題" for k, v in distribution.items()) or "—"
