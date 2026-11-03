from app.llm import ReplyError
from app.pipeline import AskResult, ask


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
        sql="SELECT count(*) AS n FROM cafes WHERE city = '台北市'",
        columns=["n"],
        rows=[[160]],
    )
    assert gen.questions == ["台北市有幾家咖啡店？"]
    assert ex.calls == ["SELECT count(*) AS n FROM cafes WHERE city = '台北市'"]


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

    assert result == AskResult(status="error", message="模型回覆的 SQL 是空的")
    assert ex.calls == []
