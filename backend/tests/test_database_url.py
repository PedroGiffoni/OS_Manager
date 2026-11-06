from app.db import normalize_database_url


def test_normalizes_render_postgres_scheme_for_psycopg3():
    assert normalize_database_url("postgres://user:pass@host/db") == (
        "postgresql+psycopg://user:pass@host/db"
    )
    assert normalize_database_url("postgresql://user:pass@host/db") == (
        "postgresql+psycopg://user:pass@host/db"
    )


def test_keeps_sqlite_and_explicit_drivers_unchanged():
    assert normalize_database_url("sqlite:///./data/os_manager.db") == (
        "sqlite:///./data/os_manager.db"
    )
    assert normalize_database_url("postgresql+psycopg://user:pass@host/db") == (
        "postgresql+psycopg://user:pass@host/db"
    )
