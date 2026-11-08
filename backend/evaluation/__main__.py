"""Evaluate the full pipeline against the golden set with real Bedrock and the demo database.

    uv --directory backend run python -m evaluation --dry-run       # reference SQL only, no model calls
    uv --directory backend run python -m evaluation --only q01,q12  # a subset
    uv --directory backend run python -m evaluation                 # the full, paid run

Needs the same settings as the API (AWS credentials, BEDROCK_*, DATABASE_URL as genbi_reader).
"""

import argparse
import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

from evaluation.golden import GoldenSetError, load_golden_set
from evaluation.metrics import QuestionOutcome, summarize
from evaluation.preflight import UnsafeDatabaseUrl, check_database_url
from evaluation.report import RunInfo, write_reports
from evaluation.runner import dry_run, estimate, run_eval, select

DEFAULT_GOLDEN = Path(__file__).resolve().parent / "golden.yaml"
# Every run lands here, outside version control; notable runs are summarised in RESULTS.md by hand.
REPORTS_DIR = Path(__file__).resolve().parent / "reports"


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="python -m evaluation", description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="only check that reference SQL runs; no model calls")
    parser.add_argument("--only", type=_ids, help="comma-separated question ids, e.g. q01,q12")
    parser.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN, help="golden set YAML file")
    return parser.parse_args(argv)


def _ids(value: str) -> set[str]:
    return {part.strip() for part in value.split(",") if part.strip()}


async def main(argv: list[str]) -> int:
    from app.config import Settings
    from app.main import build_dependencies
    from app.pipeline import ask

    args = parse_args(argv)
    try:
        questions = select(load_golden_set(args.golden), args.only)
    except (GoldenSetError, ValueError) as e:
        print(f"golden set error: {e}", file=sys.stderr)
        return 2

    settings = Settings()
    try:
        check_database_url(settings.database_url, db_port=settings.db_port)
    except UnsafeDatabaseUrl as e:
        print(f"database settings error: {e}", file=sys.stderr)
        return 2
    deps = build_dependencies(settings)
    try:
        if args.dry_run:
            checks = await dry_run(questions, reference_db=deps.executor)
            for c in checks:
                print(f"{c.question.id} {'ok' if c.ok else 'FAIL'} {c.rows if c.ok else c.error}")
            return 0 if all(c.ok for c in checks) else 1

        plan = estimate(questions, max_retries=settings.max_sql_retries, guardrail=deps.input_guard is not None)
        print(
            f"{plan.questions} questions, model {settings.bedrock_model_id}: "
            f"{plan.guardrail_checks} guardrail checks, {plan.min_model_calls}-{plan.max_model_calls} model calls"
        )

        async def ask_one(question: str):
            return await ask(
                question,
                deps.generator,
                deps.executor,
                input_guard=deps.input_guard,
                max_retries=settings.max_sql_retries,
            )

        started_at = datetime.now(UTC)
        outcomes = await run_eval(questions, ask=ask_one, reference_db=deps.executor, on_progress=_print_progress)
    finally:
        await deps.executor.close()

    summary = summarize(outcomes)
    guardrail = f"{settings.bedrock_guardrail_id}:{settings.bedrock_guardrail_version}" if deps.input_guard else None
    info = RunInfo(
        started_at=started_at,
        model_id=settings.bedrock_model_id,
        guardrail=guardrail,
        max_sql_retries=settings.max_sql_retries,
        golden_file=str(args.golden),
    )
    json_path, md_path = write_reports(REPORTS_DIR, info, summary, outcomes)
    print(f"accuracy {summary.correct}/{summary.total}, p95 {summary.p95_ms} ms, cost ${summary.total_cost_usd}")
    print(f"reports: {md_path} {json_path}")
    return 0


def _print_progress(outcome: QuestionOutcome) -> None:
    mark = "ok " if outcome.correct else "NG "
    detail = outcome.error or outcome.reason or ""
    ms = outcome.usage.elapsed_ms if outcome.usage else "-"
    print(f"{outcome.question.id} {mark} attempts={outcome.attempts} {ms}ms {detail}")


if __name__ == "__main__":
    sys.exit(asyncio.run(main(sys.argv[1:])))
