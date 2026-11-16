"""Alembic environment: uses the application's database settings."""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context

from app.database import get_engine
from app.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def render_item(type_, obj, autogen_context):
    """Render app-specific column types as plain SQL types in migrations."""
    if type_ == "type":
        from app.db_types import EncryptedText, UTCDateTime  # noqa: PLC0415

        if isinstance(obj, EncryptedText):
            return "sa.Text()"
        if isinstance(obj, UTCDateTime):
            return "sa.DateTime(timezone=True)"
    return False


def run_migrations_offline() -> None:
    engine = get_engine()
    context.configure(url=engine.url, target_metadata=target_metadata, literal_binds=True,
                      dialect_opts={"paramstyle": "named"}, render_as_batch=engine.dialect.name == "sqlite",
                      render_item=render_item)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    engine = get_engine()
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata,
                          render_as_batch=connection.dialect.name == "sqlite", compare_type=True,
                          render_item=render_item)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
