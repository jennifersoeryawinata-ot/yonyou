import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy import text
from sqlmodel import SQLModel, create_engine
from models import *

from configs.config import settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = SQLModel.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.

exclude_tables = config.get_section('alembic:exclude').get('tables', '').split(',')

def include_object(object, name, type_, *args, **kwargs):
    if type_ == "table" and name == "alembic_version":
        return False
    
    if type_ == "table":
        table_schema = object.schema or target_metadata.schema
        if table_schema != target_metadata.schema:
            return False 
    # if type_ == "table" and obj.schema != target_metadata.schema:
    #     return False
    return True
    # return not (type_ == 'table' and name in exclude_tables)

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = settings.DB_CONFIG
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        version_table_schema=settings.POSTGRES_SCHEMA,
        include_schemas=True
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    # Buat schema jika belum ada dan set search_path
    connection.execute(text(f"CREATE SCHEMA IF NOT EXISTS {settings.POSTGRES_SCHEMA}"))
    connection.execute(text(f"SET search_path TO {settings.POSTGRES_SCHEMA}"))
    connection.commit()
    context.configure(
        connection=connection, 
        target_metadata=target_metadata,
        include_object=include_object,
        version_table_schema=settings.POSTGRES_SCHEMA,
        include_schemas=True
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = AsyncEngine(
        create_engine(
            settings.DB_CONFIG, 
            echo=True, 
            future=True, 
            connect_args={
                "server_settings": {
                    "search_path": settings.POSTGRES_SCHEMA
                }
            },
        )
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
        await connection.commit()

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
