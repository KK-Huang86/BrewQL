import pytest

from app.db import DatabaseUnavailable, PgExecutor


async def test_unreachable_database_is_reported_as_unavailable_not_as_a_query_error():
    # Port 1 on localhost refuses at once; no real database is involved.
    ex = PgExecutor("postgresql://nobody:x@127.0.0.1:1/none")
    try:
        with pytest.raises(DatabaseUnavailable):
            await ex.run("SELECT 1")
    finally:
        await ex.close()


@pytest.mark.parametrize("ms", [0, -1])
def test_non_positive_statement_timeout_is_rejected(ms):
    # In Postgres 0 means "no timeout", the opposite of what a caller would want.
    with pytest.raises(ValueError, match="statement_timeout_ms"):
        PgExecutor("postgresql://x@127.0.0.1:1/none", statement_timeout_ms=ms)
