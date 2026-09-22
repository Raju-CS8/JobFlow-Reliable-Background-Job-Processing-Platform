"""Database connection and session management."""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool
from jobflow.db.models import Base
from jobflow.config import get_config

# Get configuration
config = get_config()

# Create engine
engine = create_engine(
    config.database_url,
    echo=False,
    poolclass=NullPool,  # Disable connection pooling for worker processes
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_session() -> Session:
    """
    Get a database session.
    Use as a context manager or dependency injection.
    """
    return SessionLocal()


def init_db() -> None:
    """
    Initialize the database by creating all tables.
    Idempotent: safe to call multiple times.
    """
    Base.metadata.create_all(bind=engine)


def drop_db() -> None:
    """
    Drop all tables.
    Use only for testing.
    """
    Base.metadata.drop_all(bind=engine)


def get_engine():
    """Get the SQLAlchemy engine."""
    return engine