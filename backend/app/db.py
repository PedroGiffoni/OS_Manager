import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session as ORMSession, sessionmaker, with_loader_criteria

LOCAL_DATABASE_URL = "postgresql+psycopg://os_manager:os_manager@localhost:5432/os_manager"
DATABASE_URL = os.getenv("DATABASE_URL", LOCAL_DATABASE_URL)


def normalize_database_url(value: str) -> str:
    if value.startswith("postgres://"):
        return "postgresql+psycopg://" + value.removeprefix("postgres://")
    if value.startswith("postgresql://"):
        return "postgresql+psycopg://" + value.removeprefix("postgresql://")
    return value


DATABASE_URL = normalize_database_url(DATABASE_URL)
if not DATABASE_URL.startswith("postgresql+psycopg://") and not DATABASE_URL.startswith("sqlite"):
    raise ValueError("DATABASE_URL deve apontar para PostgreSQL com psycopg.")

engine_options = {
    "pool_pre_ping": True,
}
if DATABASE_URL.startswith("postgresql+"):
    engine_options.update(pool_size=3, max_overflow=0, pool_timeout=30)
elif DATABASE_URL.startswith("sqlite"):
    # Explicit SQLite URLs remain available to isolated legacy unit/migration fixtures.
    engine_options["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **engine_options)
if DATABASE_URL.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def configure_sqlite(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA busy_timeout=5000")


SessionLocal = sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


@event.listens_for(ORMSession, "do_orm_execute")
def enforce_active_board_scope(execute_state):
    """Apply board isolation to all ORM reads and bulk writes in web requests."""
    board_id = execute_state.session.info.get("board_id")
    if board_id is None or execute_state.execution_options.get("skip_board_scope"):
        return
    if execute_state.is_select:
        options = [
            with_loader_criteria(
                mapper.class_,
                mapper.class_.board_id == board_id,
                include_aliases=True,
            )
            for mapper in Base.registry.mappers
            if hasattr(mapper.class_, "board_id") and mapper.class_.__name__ != "BoardMember"
        ]
        execute_state.statement = execute_state.statement.options(*options)
    elif execute_state.is_update or execute_state.is_delete:
        mapper = execute_state.bind_mapper
        if mapper is not None and hasattr(mapper.class_, "board_id") and mapper.class_.__name__ != "BoardMember":
            execute_state.statement = execute_state.statement.where(mapper.class_.board_id == board_id)


@event.listens_for(ORMSession, "before_flush")
def assign_active_board(session, _flush_context, _instances):
    """Stamp new scoped records and reject writes across the active board."""
    board_id = session.info.get("board_id")
    if board_id is None:
        return
    for row in session.new:
        if hasattr(type(row), "board_id"):
            # Membership rows are managed only by administrator-only board routes;
            # they must be writable for any board, independently of the selected one.
            if type(row).__name__ == "BoardMember" and session.info.get("user_role") == "admin":
                continue
            if type(row).__name__ == "Audit" and getattr(row, "entity", None) == "board" and session.info.get("user_role") == "admin":
                continue
            if getattr(row, "board_id", None) is None:
                row.board_id = board_id
            elif row.board_id != board_id:
                raise ValueError("Não é permitido gravar dados em outro quadro.")
    for row in session.dirty:
        if hasattr(type(row), "board_id") and row.board_id != board_id:
            raise ValueError("Não é permitido alterar dados de outro quadro.")


def get_db():
    with SessionLocal() as session:
        yield session
