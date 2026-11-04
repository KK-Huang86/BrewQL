from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
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


def test_dates_serialize_as_iso_strings_and_decimals_as_numbers():
    client = client_with(
        FakeGenerator(),
        FakeExecutor(
            ["day", "at", "rating"],
            [[date(2026, 5, 1), datetime(2026, 5, 1, 9, 30, tzinfo=UTC), Decimal("4.5")]],
        ),
    )

    response = client.post("/api/ask", json={"question": "q"})

    assert response.json()["rows"] == [["2026-05-01", "2026-05-01T09:30:00Z", 4.5]]


@pytest.mark.parametrize(
    "body",
    [{}, {"question": ""}, {"question": "   "}, {"question": "問" * 1001}, {"question": 123}],
)
def test_invalid_question_is_422_and_never_reaches_the_model(body):
    response = client_with().post("/api/ask", json=body)

    assert response.status_code == 422


def test_sql_rejected_by_the_guard_is_200_with_error_status():
    client = client_with(FakeGenerator(sql="DELETE FROM cafes"), ExplodingDependency())

    response = client.post("/api/ask", json={"question": "刪掉所有店"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "error"
    assert body["sql"] == "DELETE FROM cafes"
    assert body["message"]


def test_bedrock_failure_is_5xx_and_logged(caplog):
    client = TestClient(
        create_app(
            generator=FakeGenerator(exc=RuntimeError("AccessDeniedException")),
            executor=ExplodingDependency(),
            cors_origins=[],
        ),
        raise_server_exceptions=False,
    )

    response = client.post("/api/ask", json={"question": "q"})

    assert 500 <= response.status_code < 600
    assert "AccessDeniedException" not in response.text  # internal detail stays in the log
    assert any("AccessDeniedException" in (r.exc_text or str(r.exc_info)) for r in caplog.records)


def test_bedrock_failure_body_keeps_the_response_contract():
    client = TestClient(
        create_app(generator=FakeGenerator(exc=RuntimeError("boom")), executor=ExplodingDependency(), cors_origins=[]),
        raise_server_exceptions=False,
    )

    response = client.post("/api/ask", json={"question": "q"})

    assert response.status_code == 502
    assert response.json() == {
        "status": "error",
        "sql": None,
        "columns": [],
        "rows": [],
        "message": "模型服務暫時無法使用，請稍後再試",
    }


def preflight(client, origin, method="POST"):
    return client.options(
        "/api/ask",
        headers={"Origin": origin, "Access-Control-Request-Method": method},
    )


def test_cors_allows_the_configured_frontend_for_get_and_post():
    response = preflight(client_with(origins=["http://localhost:5173"]), "http://localhost:5173")

    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert set(response.headers["access-control-allow-methods"].replace(" ", "").split(",")) == {"GET", "POST"}


def test_cors_ignores_unknown_origins():
    response = preflight(client_with(origins=["http://localhost:5173"]), "https://evil.example")

    assert "access-control-allow-origin" not in response.headers


def test_cors_does_not_allow_other_methods():
    response = preflight(client_with(origins=["http://localhost:5173"]), "http://localhost:5173", method="DELETE")

    assert response.status_code == 400


def test_production_app_starts_and_is_healthy_without_database_or_aws(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://nobody:x@127.0.0.1:1/none")
    monkeypatch.setenv("AWS_REGION", "us-east-1")

    from app.main import build_app

    response = TestClient(build_app()).get("/health")

    assert response.json() == {"status": "ok"}


class DownExecutor:
    async def run(self, sql):
        from app.db import DatabaseUnavailable

        raise DatabaseUnavailable("OSError: connection refused")


def test_database_outage_is_503_with_its_own_message(caplog):
    client = TestClient(
        create_app(generator=FakeGenerator(), executor=DownExecutor(), cors_origins=[]),
        raise_server_exceptions=False,
    )

    response = client.post("/api/ask", json={"question": "q"})

    assert response.status_code == 503
    assert response.json() == {
        "status": "error",
        "sql": None,
        "columns": [],
        "rows": [],
        "message": "資料庫暫時無法使用，請稍後再試",
    }
    assert "connection refused" not in response.text
    assert any("connection refused" in (r.exc_text or "") for r in caplog.records)
