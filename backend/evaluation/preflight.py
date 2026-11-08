"""Check DATABASE_URL before the eval connects: it runs outside compose, from a hand-written .env."""

from urllib.parse import urlsplit

READER = "genbi_reader"
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
POSTGRES_DEFAULT_PORT = 5432


class UnsafeDatabaseUrl(Exception):
    """DATABASE_URL would reach the wrong database or role; nothing was sent to it."""


def check_database_url(url: str, *, db_port: int) -> None:
    # Messages name the problem only: the URL holds the password.
    parts = urlsplit(url.strip())
    if not parts.scheme.startswith("postgres") or not parts.hostname:
        raise UnsafeDatabaseUrl("DATABASE_URL is missing or not a postgresql:// URL")
    if parts.username != READER:
        raise UnsafeDatabaseUrl(f"DATABASE_URL must connect as {READER}, not as {parts.username or '(no user)'}")
    try:
        port = parts.port or POSTGRES_DEFAULT_PORT
    except ValueError:
        # urlsplit only parses the port on access; turn a crash into a clear refusal.
        raise UnsafeDatabaseUrl("DATABASE_URL has a port that is not a number") from None
    if parts.hostname in LOCAL_HOSTS and port != db_port:
        # A local Postgres on another port belongs to some other project.
        raise UnsafeDatabaseUrl(f"DATABASE_URL uses local port {port}, but DB_PORT is {db_port}")
