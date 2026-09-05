"""Database access and initialization for RetailIQ using SQLite."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Generator
from src.config import DATABASE_PATH, DATA_DIR


def ensure_data_directory() -> None:
    """Ensure the data directory exists."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def get_connection(db_path: str | Path = DATABASE_PATH) -> sqlite3.Connection:
    """Get a connection to the SQLite database."""
    ensure_data_directory()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db_cursor(db_path: str | Path = DATABASE_PATH) -> Generator[sqlite3.Cursor, None, None]:
    """Context manager for obtaining a database cursor."""
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: str | Path = DATABASE_PATH) -> None:
    """Initialize SQLite database tables (placeholder for future stages)."""
    ensure_data_directory()
    # Placeholder: schema definitions will be added when synthetic data is introduced in later stages
    with get_db_cursor(db_path) as cursor:
        cursor.execute("SELECT 1")
