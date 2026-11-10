"""Evaluating rag (rag-knowledge-base): pick the mode, record it, compare two runs, refuse leaked examples."""

import json
from datetime import UTC, datetime

import pytest

from app.knowledge import KnowledgeDoc
from app.pipeline import AskResult, Source
from evaluation.__main__ import parse_args
from evaluation.compare_runs import compare_runs, to_markdown
from evaluation.golden import GoldenQuestion
from evaluation.leaks import ExampleLeak, check_leaks
from evaluation.metrics import summarize
from evaluation.report import RunInfo, to_json
from evaluation.runner import run_eval
from tests.test_eval_report import RIGHT, WRONG
from tests.test_eval_runner import COUNT, FakeAsk, ReferenceDb, usage

# --- choosing and recording the mode ---------------------------------------------------------------


def test_mode_defaults_to_the_settings_and_accepts_static_or_rag():
    assert parse_args([]).mode is None
    assert parse_args(["--mode", "rag"]).mode == "rag"
    with pytest.raises(SystemExit):
        parse_args(["--mode", "vector"])


def run_info(mode: str) -> RunInfo:
    return RunInfo(
        started_at=datetime(2026, 11, 10, tzinfo=UTC),
        model_id="m",
        guardrail=None,
        max_sql_retries=1,
        golden_file="golden.yaml",
        prompt_mode=mode,
    )


def test_report_records_the_mode():
    report = to_json(run_info("rag"), summarize([RIGHT]), [RIGHT])

    assert report["run"]["prompt_mode"] == "rag"


async def test_report_lists_the_knowledge_each_question_used():
    answer = AskResult(
        status="ok",
        sql="SELECT ...",
        rows=[[160]],
        attempts=1,
        usage=usage(),
        sources=[Source(id="schema-cafes", kind="schema", title="cafes")],
    )
    outcomes = await run_eval([COUNT], ask=FakeAsk({COUNT.question: answer}), reference_db=ReferenceDb())

    report = to_json(run_info("rag"), summarize(outcomes), outcomes)

    assert report["questions"][0]["sources"] == ["schema-cafes"]


# --- comparing two runs ----------------------------------------------------------------------------


def report(mode: str, outcomes) -> dict:
    # Round-trip through JSON: compare_runs reads saved report files.
    return json.loads(json.dumps(to_json(run_info(mode), summarize(outcomes), outcomes)))


def flipped(outcome, correct: bool):
    from dataclasses import replace

    return replace(outcome, correct=correct, cost_usd=(outcome.cost_usd or 0) / 2)


def test_comparison_lists_questions_that_flipped_each_way():
    base = report("static", [RIGHT, WRONG])
    other = report("rag", [flipped(RIGHT, False), flipped(WRONG, True)])

    diff = compare_runs(base, other)

    assert diff.fixed == ["q08"]
    assert diff.broken == ["q01"]
    assert (diff.base.correct, diff.other.correct) == (1, 1)


def test_comparison_reports_cost_latency_and_per_difficulty_accuracy():
    diff = compare_runs(report("static", [RIGHT, WRONG]), report("rag", [RIGHT, flipped(WRONG, True)]))

    assert diff.base.mode == "static" and diff.other.mode == "rag"
    assert diff.by_difficulty["medium"] == ((0, 1), (1, 1))
    assert diff.other.avg_cost_usd < diff.base.avg_cost_usd
    markdown = to_markdown(diff)
    assert "q08" in markdown
    assert "從錯變對" in markdown and "從對變錯" in markdown


def test_comparison_refuses_runs_over_different_question_sets():
    with pytest.raises(ValueError, match="q08"):
        compare_runs(report("static", [RIGHT, WRONG]), report("rag", [RIGHT]))


# --- example leaks -------------------------------------------------------------------------------


def example(question: str) -> KnowledgeDoc:
    return KnowledgeDoc(id="example-x", kind="example", title=question, content="SELECT 1")


@pytest.mark.parametrize("variant", ["台北市有幾家咖啡店？", " 台北市有幾家咖啡店? ", "台北市有幾家咖啡店"])
def test_an_example_matching_a_golden_question_stops_the_run(variant):
    golden = [GoldenQuestion(id="q01", difficulty="easy", question="台北市有幾家咖啡店？", sql="SELECT 1")]

    with pytest.raises(ExampleLeak, match="example-x.*q01"):
        check_leaks(golden, [example(variant)])


def test_different_questions_and_non_examples_pass():
    golden = [GoldenQuestion(id="q01", difficulty="easy", question="台北市有幾家咖啡店？", sql="SELECT 1")]
    glossary = KnowledgeDoc(id="g", kind="glossary", title="台北市有幾家咖啡店？", content="x")

    check_leaks(golden, [example("新北市有幾家咖啡店？"), glossary])


def test_repo_examples_do_not_leak_golden_questions():
    from app.knowledge import KNOWLEDGE_DIR, load_knowledge
    from evaluation.__main__ import DEFAULT_GOLDEN
    from evaluation.golden import load_golden_set

    check_leaks(load_golden_set(DEFAULT_GOLDEN), load_knowledge(KNOWLEDGE_DIR))
