"""
Application logging configuration and utilities.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional


class DatabaseLogHandler(logging.Handler):
    """Logging handler that writes log records to the ApplicationLog table."""

    def __init__(self, level=logging.NOTSET):
        super().__init__(level)
        self._enabled = False

    def enable(self):
        self._enabled = True

    def emit(self, record):
        if not self._enabled:
            return
        try:
            from database.session import get_db
            from models.models import ApplicationLog

            session = get_db()
            try:
                log_entry = ApplicationLog(
                    timestamp=datetime.fromtimestamp(record.created),
                    level=record.levelname,
                    logger_name=record.name,
                    message=self.format(record) if self.formatter else record.getMessage(),
                    module=record.module,
                    function=record.funcName,
                    line_number=record.lineno,
                )
                session.add(log_entry)
                session.commit()
            except Exception:
                session.rollback()
            finally:
                session.close()
        except Exception:
            pass


_db_handler: Optional[DatabaseLogHandler] = None


def setup_logging(log_level: int = logging.INFO, log_to_file: bool = True) -> None:
    """
    Set up application logging configuration.

    Args:
        log_level: Logging level (default: INFO)
        log_to_file: Whether to log to file in addition to console
    """
    global _db_handler

    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler (optional)
    if log_to_file:
        log_file = log_dir / f"tncut_{datetime.now().strftime('%Y_%m_%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Database handler
    _db_handler = DatabaseLogHandler(level=log_level)
    _db_handler.setFormatter(formatter)
    root_logger.addHandler(_db_handler)

    # Reduce verbosity of some noisy libraries
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)

    # Log startup message
    logging.info("TNCut application logging initialized")
    logging.info(f"Log level: {logging.getLevelName(log_level)}")
    if log_to_file:
        logging.info(f"Logging to file: {log_file}")


def enable_db_logging():
    """Enable the database logging handler (call after database is initialized)."""
    if _db_handler:
        _db_handler.enable()


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
