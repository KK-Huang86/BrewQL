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
