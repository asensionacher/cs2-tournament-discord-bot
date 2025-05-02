import sqlite3
from pathlib import Path
from typing import Optional

class DatabaseManager:
    def __init__(self, db_path: str = "./data/tournament.db"):
        self.db_path = db_path
        self._create_tables()

    def _get_sql_file_path(self) -> Path:
        """Locate the init-db.sql file"""
        return Path(__file__).parent.parent / "sql" / "init-db.sql"

    def _read_sql_file(self) -> str:
        """Read the SQL initialization file"""
        with open(self._get_sql_file_path(), 'r', encoding='utf-8') as f:
            return f.read()

    def _create_tables(self) -> None:
        """Initialize database using external SQL file"""
        try:
            with self.get_connection() as conn:
                conn.executescript(self._read_sql_file())
                conn.commit()
        except FileNotFoundError:
            raise RuntimeError(f"SQL initialization file not found at {self._get_sql_file_path()}")
        except sqlite3.Error as e:
            raise RuntimeError(f"Database initialization failed: {e}")

    def get_connection(self) -> sqlite3.Connection:
        """Get a thread-safe database connection"""
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def reset_database(self) -> None:
        """Drop all tables and reinitialize (for testing)"""
        with self.get_connection() as conn:
            conn.executescript("""
                PRAGMA foreign_keys = OFF;
                DROP TABLE IF EXISTS team;
                DROP TABLE IF EXISTS player;
                -- Add all other tables to drop
                PRAGMA foreign_keys = ON;
            """)
        self._create_tables()  # Recreate fresh tables
