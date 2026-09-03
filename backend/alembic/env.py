from logging.config import fileConfig
from pathlib import Path
import os

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import URL

from backend.app.db.base import Base
from backend.app.models import (
    AgentDecision,
    AuditLog,
    Customer,
    RecoveryAction,
    RecoveryCase,
    Transaction,
    User,
    WebhookEvent,
)


# =========================================================
# PROJECT PATHS
# =========================================================

# env.py is located at:
# backend/alembic/env.py
#
# Therefore:
#   parents[0] -> backend/alembic
#   parents[1] -> backend
#   parents[2] -> project root
#
PROJECT_ROOT = Path(__file__).resolve().parents[2]

ENV_FILE = PROJECT_ROOT / ".env"


# =========================================================
# LOAD ENVIRONMENT VARIABLES
# =========================================================

# Explicitly load the project's .env file.
#
# This is important because Alembic may not always execute
# with the same working-directory assumptions as the normal
# application process.
load_dotenv(dotenv_path=ENV_FILE, override=False)


# =========================================================
# ALEMBIC CONFIGURATION
# =========================================================

config = context.config


# Configure Python logging using alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


# =========================================================
# SQLALCHEMY METADATA
# =========================================================

# Importing all models above ensures that every model is
# registered in Base.metadata before Alembic compares the
# database schema with the application schema.
target_metadata = Base.metadata


# =========================================================
# DATABASE CONFIGURATION
# =========================================================

def get_database_url() -> URL:
    """
    Build the PostgreSQL SQLAlchemy URL directly from the
    project's environment variables.

    URL.create() is intentionally used instead of manually
    constructing a connection string. This safely handles
    special characters in the database password.
    """

    postgres_user = os.getenv("POSTGRES_USER")
    postgres_password = os.getenv("POSTGRES_PASSWORD")
    postgres_host = os.getenv("POSTGRES_HOST")
    postgres_port = os.getenv("POSTGRES_PORT")
    postgres_db = os.getenv("POSTGRES_DB")

    # -----------------------------------------------------
    # Validate required variables
    # -----------------------------------------------------

    missing_variables = []

    if not postgres_user:
        missing_variables.append("POSTGRES_USER")

    if not postgres_password:
        missing_variables.append("POSTGRES_PASSWORD")

    if not postgres_host:
        missing_variables.append("POSTGRES_HOST")

    if not postgres_port:
        missing_variables.append("POSTGRES_PORT")

    if not postgres_db:
        missing_variables.append("POSTGRES_DB")

    if missing_variables:
        raise RuntimeError(
            "Missing required database environment variables: "
            + ", ".join(missing_variables)
            + f"\nExpected .env file: {ENV_FILE}"
        )

    # -----------------------------------------------------
    # Validate port
    # -----------------------------------------------------

    try:
        port = int(postgres_port)
    except ValueError as exc:
        raise RuntimeError(
            f"POSTGRES_PORT must be a number. Got: {postgres_port!r}"
        ) from exc

    # -----------------------------------------------------
    # Create SQLAlchemy URL safely
    # -----------------------------------------------------

    return URL.create(
        drivername="postgresql+psycopg",
        username=postgres_user,
        password=postgres_password,
        host=postgres_host,
        port=port,
        database=postgres_db,
    )


# =========================================================
# OFFLINE MIGRATIONS
# =========================================================

def run_migrations_offline() -> None:
    """
    Run migrations without creating a live database
    connection.
    """

    database_url = get_database_url()

    context.configure(
        url=database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={
            "paramstyle": "named",
        },
    )

    with context.begin_transaction():
        context.run_migrations()


# =========================================================
# ONLINE MIGRATIONS
# =========================================================

def run_migrations_online() -> None:
    """
    Run migrations using a live PostgreSQL connection.
    """

    database_url = get_database_url()

    # -----------------------------------------------------
    # Safe diagnostic output
    # -----------------------------------------------------
    #
    # The password itself is NEVER printed.
    #

    print()
    print("=" * 60)
    print("ALEMBIC DATABASE CONFIGURATION")
    print("=" * 60)

    print(
        "PROJECT ROOT:",
        PROJECT_ROOT,
    )

    print(
        ".ENV FILE:",
        ENV_FILE,
    )

    print(
        ".ENV EXISTS:",
        ENV_FILE.exists(),
    )

    print(
        "DATABASE:",
        database_url.render_as_string(hide_password=True),
    )

    print(
        "USERNAME:",
        database_url.username,
    )

    print(
        "HOST:",
        database_url.host,
    )

    print(
        "PORT:",
        database_url.port,
    )

    print(
        "DATABASE NAME:",
        database_url.database,
    )

    print(
        "PASSWORD EXISTS:",
        database_url.password is not None,
    )

    print(
        "PASSWORD LENGTH:",
        len(database_url.password or ""),
    )

    print("=" * 60)
    print()

    # -----------------------------------------------------
    # Create SQLAlchemy engine
    # -----------------------------------------------------

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
    )

    # -----------------------------------------------------
    # Connect and run migrations
    # -----------------------------------------------------

    try:
        with engine.connect() as connection:

            print("ALEMBIC DATABASE CONNECTION OK")
            print()

            context.configure(
                connection=connection,
                target_metadata=target_metadata,
            )

            with context.begin_transaction():
                context.run_migrations()

    finally:
        engine.dispose()


# =========================================================
# RUN
# =========================================================

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()