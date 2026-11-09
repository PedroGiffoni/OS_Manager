from alembic import context
from app.db import engine, Base
from app import models

with engine.connect() as connection:
    sqlite = connection.dialect.name == "sqlite"
    if sqlite:
        # Several historical migrations rebuild tables that are referenced by
        # foreign keys. SQLite only permits those DDL operations with enforcement
        # temporarily disabled, so check the complete graph before restoring it.
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.commit()
    try:
        context.configure(connection=connection, target_metadata=Base.metadata, render_as_batch=True)
        with context.begin_transaction():
            context.run_migrations()
        if sqlite:
            violations = list(connection.exec_driver_sql("PRAGMA foreign_key_check"))
            if violations:
                raise RuntimeError(f"SQLite migration left foreign-key violations: {violations[:10]}")
    finally:
        if sqlite:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            connection.commit()
