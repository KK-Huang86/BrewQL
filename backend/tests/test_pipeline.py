import pytest

from app.db import QueryError
from app.llm import ReplyError
from app.pipeline import AskResult, InvalidQuestion, ask


class FakeGenerator:
    def __init__(self, sql="SELECT 1", exc=None):
        self.sql, self.exc, self.questions = sql, exc, []

    async def generate(self, question):
        self.questions.append(question)
        if self.exc:
            raise self.exc
        return self.sql


class FakeExecutor:
    def __init__(self, columns=("n",), rows=((1,),), exc=None):
        self.columns, self.rows, self.exc, self.calls = list(columns), [list(r) for r in rows], exc, []

    async def run(self, sql):
        self.calls.append(sql)
        if self.exc:
            raise self.exc
        return self.columns, self.rows


async def test_question_becomes_sql_and_result():
    gen = FakeGenerator(sql="SELECT count(*) AS n FROM cafes WHERE city = '台北市'")
    ex = FakeExecutor(columns=["n"], rows=[[160]])

    result = await ask("台北市有幾家咖啡店？", gen, ex)

    assert result == AskResult(
        status="ok",
        sql="SELECT COUNT(*) AS n FROM cafes WHERE city = '台北市' LIMIT 1000",
        columns=["n"],
        rows=[[160]],
    )
    assert gen.questions == ["台北市有幾家咖啡店？"]
    # The guard's rewrite (row cap) is what runs and what the user sees.
    assert ex.calls == ["SELECT COUNT(*) AS n FROM cafes WHERE city = '台北市' LIMIT 1000"]


async def test_sql_rejected_by_the_guard_is_never_executed():
    ex = FakeExecutor()

    result = await ask("把咖啡店都刪掉", FakeGenerator(sql="DELETE FROM cafes"), ex)

    assert result.status == "error"
    assert result.sql == "DELETE FROM cafes"
    assert result.message
    assert ex.calls == []


async def test_reply_without_usable_sql_is_an_error_and_nothing_runs():
    ex = FakeExecutor()

    result = await ask("q", FakeGenerator(exc=ReplyError("模型回覆的 SQL 是空的")), ex)

    assert result == AskResult(status="error", message="模型回覆的 SQL 是空的", error_kind="generation")
    assert ex.calls == []


async def test_database_error_is_reported_with_the_sql_but_not_the_raw_error(caplog):
    ex = FakeExecutor(exc=QueryError('UndefinedColumnError: column "x" does not exist'))

    result = await ask("q", FakeGenerator(sql="SELECT x FROM cafes"), ex)

    assert result.status == "error"
    assert result.sql == "SELECT x FROM cafes LIMIT 1000"
    # Raw Postgres text reveals schema internals; users get a generic hint, the log keeps the detail.
    assert result.message == "查詢執行失敗，請換個問法再試"
    assert any('column "x" does not exist' in r.getMessage() for r in caplog.records)


@pytest.mark.parametrize("question", ["", "   ", "\n\t", "問" * 1001])
async def test_blank_or_too_long_question_never_reaches_the_model(question):
    gen = FakeGenerator()

    with pytest.raises(InvalidQuestion):
        await ask(question, gen, FakeExecutor())

    assert gen.questions == []


async def test_question_is_trimmed_and_1000_chars_is_allowed():
    gen = FakeGenerator()

    await ask("  " + "問" * 1000 + "  ", gen, FakeExecutor())

    assert gen.questions == ["問" * 1000]


async def test_model_service_errors_propagate():
    boom = RuntimeError("ThrottlingException")

    with pytest.raises(RuntimeError) as raised:
        await ask("q", FakeGenerator(exc=boom), FakeExecutor())

    assert raised.value is boom


@pytest.mark.parametrize(
    ("generator", "executor", "kind"),
    [
        (FakeGenerator(exc=ReplyError("模型拒絕回答這個問題")), FakeExecutor(), "generation"),
        (FakeGenerator(sql="SELECT * FROM pg_shadow"), FakeExecutor(), "guardrail"),
        (FakeGenerator(sql="SELECT x FROM cafes"), FakeExecutor(exc=QueryError("UndefinedColumnError")), "query"),
    ],
)
async def test_each_error_is_tagged_with_where_it_failed(generator, executor, kind):
    result = await ask("q", generator, executor)

    assert result.status == "error"
    assert result.error_kind == kind


async def test_success_has_no_error_kind():
    result = await ask("q", FakeGenerator(sql="SELECT name FROM cafes"), FakeExecutor())

    assert result.error_kind is None
