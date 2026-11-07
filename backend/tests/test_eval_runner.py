"""Running the golden set: sequential, cheap to rehearse, and one failure never stops the run."""

import pytest

from app.input_guard import GuardrailUsage
from app.pipeline import AskResult, AskUsage
from evaluation.golden import GoldenQuestion
from evaluation.runner import dry_run, estimate, run_eval, select

HAIKU_US = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
COUNT = GoldenQuestion(id="q01", difficulty="easy", question="台北市幾家", sql="SELECT COUNT(*) FROM cafes")
DISTRICTS = GoldenQuestion(id="q02", difficulty="easy", question="新北市行政區", sql="SELECT district FROM cafes")
REFUSE = GoldenQuestion(id="q12", difficulty="refuse", question="刪除", expect="refused")
BROKEN = GoldenQuestion(id="q09", difficulty="medium", question="壞掉", sql="SELECT no_such_column FROM cafes")


class ReferenceDb:
    """Reference SQL runs here; rows keyed by a fragment of the (guard-rewritten) SQL."""

    def __init__(self):
        self.calls = []

    async def run(self, sql):
        from app.db import QueryError

        self.calls.append(sql)
        if "no_such_column" in sql:
            raise QueryError('UndefinedColumnError: column "no_such_column" does not exist')
        if "COUNT" in sql:
            return ["count"], [[160]]
        return ["district"], [["板橋區"], ["永和區"]]


def usage():
    return AskUsage(
        model_id=HAIKU_US, input_tokens=1000, output_tokens=50, guardrail=GuardrailUsage(1, 1), elapsed_ms=900
    )


class FakeAsk:
    """Stands in for the full pipeline; answers by question text, may raise for one of them."""

    def __init__(self, answers, fail_on=()):
        self.answers, self.fail_on, self.asked = answers, set(fail_on), []

    async def __call__(self, question):
        self.asked.append(question)
        if question in self.fail_on:
            raise RuntimeError("ThrottlingException: rate exceeded")
        return self.answers[question]


def ok(rows):
    return AskResult(status="ok", sql="SELECT ...", columns=["x"], rows=rows, attempts=1, usage=usage())


def test_select_keeps_file_order_and_rejects_unknown_ids():
    questions = [COUNT, DISTRICTS, REFUSE]

    assert select(questions, None) == questions
    assert select(questions, {"q12", "q01"}) == [COUNT, REFUSE]
    with pytest.raises(ValueError, match="q99"):
        select(questions, {"q01", "q99"})


def test_estimate_shows_the_range_of_paid_calls_before_running():
    plan = estimate([COUNT, DISTRICTS, REFUSE], max_retries=1)

    assert (plan.questions, plan.guardrail_checks) == (3, 3)
    assert (plan.min_model_calls, plan.max_model_calls) == (3, 6)


async def test_answers_are_judged_against_the_reference_result():
    ask = FakeAsk({"台北市幾家": ok([[160]]), "新北市行政區": ok([["永和區"]])})

    outcomes = await run_eval([COUNT, DISTRICTS], ask=ask, reference_db=ReferenceDb())

    assert [o.correct for o in outcomes] == [True, False]
    assert outcomes[0].attempts == 1
    assert outcomes[0].usage.input_tokens == 1000
    # Priced from usage: 1000 x 1.10/M + 50 x 5.50/M + 2 x 0.15/1000
    assert outcomes[0].cost_usd == pytest.approx(0.0011 + 0.000275 + 0.0003)


async def test_reference_sql_goes_through_the_sql_guard_too():
    db = ReferenceDb()

    await run_eval([COUNT], ask=FakeAsk({"台北市幾家": ok([[160]])}), reference_db=db)

    assert db.calls == ["SELECT COUNT(*) FROM cafes LIMIT 1000"]


async def test_a_service_error_is_recorded_and_the_run_goes_on():
    ask = FakeAsk({"台北市幾家": ok([[160]]), "刪除": None}, fail_on={"新北市行政區"})
    ask.answers["刪除"] = AskResult(status="refused", message="不能修改", refusal_source="input_guardrail")

    outcomes = await run_eval([COUNT, DISTRICTS, REFUSE], ask=ask, reference_db=ReferenceDb())

    assert ask.asked == ["台北市幾家", "新北市行政區", "刪除"]
    failed = outcomes[1]
    assert (failed.correct, failed.status, failed.usage) == (False, None, None)
    assert "Throttling" in failed.error
    assert outcomes[2].correct
    assert outcomes[2].refusal_source == "input_guardrail"


async def test_expected_status_questions_need_no_reference_query():
    db = ReferenceDb()
    ask = FakeAsk({"刪除": AskResult(status="refused", message="x", refusal_source="model", attempts=1)})

    await run_eval([REFUSE], ask=ask, reference_db=db)

    assert db.calls == []


async def test_broken_reference_sql_skips_the_paid_call_and_is_reported():
    ask = FakeAsk({})

    [outcome] = await run_eval([BROKEN], ask=ask, reference_db=ReferenceDb())

    assert ask.asked == []
    assert not outcome.correct
    assert "reference" in outcome.error


async def test_progress_is_reported_after_each_question():
    seen = []
    ask = FakeAsk({"台北市幾家": ok([[160]]), "新北市行政區": ok([["永和區"]])})

    await run_eval([COUNT, DISTRICTS], ask=ask, reference_db=ReferenceDb(), on_progress=seen.append)

    assert [o.question.id for o in seen] == ["q01", "q02"]


async def test_dry_run_checks_reference_sql_without_calling_the_model():
    checks = await dry_run([COUNT, BROKEN, REFUSE], reference_db=ReferenceDb())

    assert [(c.question.id, c.ok) for c in checks] == [("q01", True), ("q09", False)]
    assert checks[0].rows == 1
    assert "no_such_column" in checks[1].error


async def test_dry_run_rejects_reference_sql_the_guard_would_block():
    unsafe = GoldenQuestion(id="q20", difficulty="easy", question="x", sql="DELETE FROM cafes")

    [check] = await dry_run([unsafe], reference_db=ReferenceDb())

    assert not check.ok
