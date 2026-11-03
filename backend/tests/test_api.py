from fastapi.testclient import TestClient

from app.main import create_app


class ExplodingDependency:
    """Any use means the endpoint touched Bedrock or the database."""

    async def generate(self, question):
        raise AssertionError("health check must not call the model")

    async def run(self, sql):
        raise AssertionError("health check must not query the database")


def client_with(generator=None, executor=None, origins=("http://localhost:5173",)):
    gen = generator or ExplodingDependency()
    ex = executor or ExplodingDependency()
    return TestClient(create_app(generator=gen, executor=ex, cors_origins=list(origins)))


def test_health_is_ok_even_when_dependencies_are_down():
    response = client_with().get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


class FakeGenerator:
    def __init__(self, sql="SELECT 1", exc=None):
        self.sql, self.exc = sql, exc

    async def generate(self, question):
        if self.exc:
            raise self.exc
        return self.sql


class FakeExecutor:
    def __init__(self, columns, rows):
        self.columns, self.rows = columns, rows

    async def run(self, sql):
        return self.columns, self.rows


def test_ask_returns_sql_columns_and_rows():
    client = client_with(
        FakeGenerator(sql="SELECT city, count(*) AS n FROM cafes GROUP BY city"),
        FakeExecutor(["city", "n"], [["台北市", 160], ["新北市", 40]]),
    )

    response = client.post("/api/ask", json={"question": "各城市有幾家咖啡店？"})

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "sql": "SELECT city, count(*) AS n FROM cafes GROUP BY city",
        "columns": ["city", "n"],
        "rows": [["台北市", 160], ["新北市", 40]],
        "message": None,
    }
