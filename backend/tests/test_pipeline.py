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
