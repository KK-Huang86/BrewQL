"""The eval connects with .env outside compose: a wrong URL must stop it before the password is sent."""

import pytest

from evaluation.preflight import UnsafeDatabaseUrl, check_database_url

READER = "postgresql://genbi_reader:pw@127.0.0.1:5434/genbi"


def test_reader_on_the_brewql_port_passes():
    check_database_url(READER, db_port=5434)


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost"])
def test_local_port_other_than_db_port_is_refused(host):
    # 5432 is often another project's Postgres on the same machine.
    with pytest.raises(UnsafeDatabaseUrl, match="DB_PORT"):
        check_database_url(f"postgresql://genbi_reader:pw@{host}:5432/genbi", db_port=5434)


def test_local_url_without_a_port_means_5432_and_is_refused():
    with pytest.raises(UnsafeDatabaseUrl, match="DB_PORT"):
        check_database_url("postgresql://genbi_reader:pw@localhost/genbi", db_port=5434)


@pytest.mark.parametrize("user", ["genbi", "postgres", ""])
def test_any_user_but_the_read_only_role_is_refused(user):
    with pytest.raises(UnsafeDatabaseUrl, match="genbi_reader"):
        check_database_url(f"postgresql://{user}:pw@127.0.0.1:5434/genbi", db_port=5434)


def test_remote_host_is_not_held_to_the_local_port():
    check_database_url("postgresql://genbi_reader:pw@db.example.internal:5432/genbi", db_port=5434)


@pytest.mark.parametrize("url", ["", "   ", "not a url"])
def test_missing_or_unreadable_url_is_refused(url):
    with pytest.raises(UnsafeDatabaseUrl, match="DATABASE_URL"):
        check_database_url(url, db_port=5434)


def test_error_never_shows_the_password():
    with pytest.raises(UnsafeDatabaseUrl) as raised:
        check_database_url("postgresql://genbi_reader:s3cret@127.0.0.1:5432/genbi", db_port=5434)

    assert "s3cret" not in str(raised.value)


async def test_eval_stops_before_building_any_connection(monkeypatch, capsys):
    import app.main
    from evaluation.__main__ import main

    def must_not_connect(_settings):
        raise AssertionError("dependencies built despite an unsafe DATABASE_URL")

    monkeypatch.setattr(app.main, "build_dependencies", must_not_connect)
    monkeypatch.setenv("DATABASE_URL", "postgresql://genbi_reader:pw@127.0.0.1:5432/genbi")
    monkeypatch.setenv("DB_PORT", "5434")

    assert await main(["--dry-run"]) == 2
    assert "DB_PORT" in capsys.readouterr().err
