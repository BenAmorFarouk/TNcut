"""
Database session management and initialization for TNCut application.
"""

import os
from pathlib import Path
from typing import Optional
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from models import Base
from utils.logger import get_logger

# Initialize logger
logger = get_logger(__name__)

# Global variables for engine and session factory
_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None


def get_database_url(db_path: str = "data/tncut.db") -> str:
    """
    Get SQLite database URL.

    Args:
        db_path: Path to SQLite database file

    Returns:
        SQLAlchemy database URL string
    """
    # Ensure the directory exists
    db_path_obj = Path(db_path)
    db_path_obj.parent.mkdir(parents=True, exist_ok=True)

    # Return SQLite URL
    return f"sqlite:///{db_path_obj.absolute()}"


def create_engine_with_config(db_path: str = "data/tncut.db", echo: bool = False) -> Engine:
    """
    Create SQLAlchemy engine with SQLite-specific configuration.

    Args:
        db_path: Path to SQLite database file
        echo: Whether to echo SQL statements (for debugging)

    Returns:
        Configured SQLAlchemy Engine instance
    """
    database_url = get_database_url(db_path)

    # SQLite-specific engine configuration
    engine = create_engine(
        database_url,
        echo=echo,
        connect_args={
            "check_same_thread": False,  # Allow multi-threaded access
        },
        poolclass=StaticPool,  # Use static pool for SQLite
        pool_pre_ping=True,  # Enable connection health checks
    )

    # Enable foreign key constraints for SQLite
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    logger.info(f"Database engine created: {database_url}")
    if echo:
        logger.info("SQL echo enabled for debugging")

    return engine


def init_database(db_path: str = "data/tncut.db", echo: bool = False) -> None:
    """
    Initialize the database engine and session factory.

    Args:
        db_path: Path to SQLite database file
        echo: Whether to echo SQL statements (for debugging)
    """
    global _engine, _SessionLocal

    if _engine is not None:
        logger.warning("Database already initialized. Reinitializing.")
        dispose_engine()

    _engine = create_engine_with_config(db_path, echo)
    _SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=_engine
    )

    # Create all tables
    Base.metadata.create_all(bind=_engine)
    logger.info("Database tables created successfully")


def get_engine() -> Engine:
    """
    Get the global database engine.

    Returns:
        SQLAlchemy Engine instance

    Raises:
        RuntimeError: If database has not been initialized
    """
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _engine


def get_session_local() -> sessionmaker:
    """
    Get the global session factory.

    Returns:
        SQLAlchemy sessionmaker

    Raises:
        RuntimeError: If database has not been initialized
    """
    if _SessionLocal is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _SessionLocal


def get_db() -> Session:
    """
    Get a new database session.

    Returns:
        SQLAlchemy Session instance

    Note:
        The caller is responsible for closing the session.
    """
    SessionLocal = get_session_local()
    return SessionLocal()


def dispose_engine() -> None:
    """Dispose of the database engine and close all connections."""
    global _engine, _SessionLocal
    if _engine is not None:
        _engine.dispose()
        _engine = None
        _SessionLocal = None
        logger.info("Database engine disposed")


# Context manager for database sessions
class DatabaseSession:
    """Context manager for automatic database session handling."""

    def __init__(self):
        self.session: Optional[Session] = None

    def __enter__(self) -> Session:
        self.session = get_db()
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            if exc_type is not None:
                self.session.rollback()
            else:
                self.session.commit()
            self.session.close()


# Convenience function for getting a session with context manager
def get_db_session() -> DatabaseSession:
    """
    Get a database session context manager.

    Returns:
        DatabaseSession context manager
    """
    return DatabaseSession()