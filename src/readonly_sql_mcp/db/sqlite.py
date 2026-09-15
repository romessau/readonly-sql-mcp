"""Read-only SQLite adapter."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from readonly_sql_mcp.db.base import QueryResult


class DatabaseError(Exception):
    """A safe database error suitable for returning to clients."""


class QueryTimeoutError(DatabaseError):
    """The database stopped a query after its configured time budget."""


class SQLiteAdapter:
    """SQLite implementation that opens an existing database read-only."""

    def __init__(self, database_path: Path, timeout_ms: int = 5_000) -> None:
        path = database_path.expanduser().resolve()
        if not path.is_file():
            raise DatabaseError("database file does not exist")
        try:
            self._connection = sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True)
            self._connection.execute("PRAGMA query_only = ON")
        except sqlite3.Error as exc:
            raise DatabaseError("unable to open database") from exc
        self._connection.row_factory = sqlite3.Row
        self._timeout_ms = timeout_ms

    def run_query(self, sql: str, row_limit: int) -> QueryResult:
        """Execute SQL within the configured time budget."""
        deadline = time.monotonic() + self._timeout_ms / 1_000
        self._connection.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1_000)
        try:
            cursor = self._connection.execute(sql)
            columns = [item[0] for item in cursor.description or []]
            rows = [list(row) for row in cursor.fetchall()]
        except sqlite3.OperationalError as exc:
            if "interrupted" in str(exc).lower():
                raise QueryTimeoutError("query exceeded the configured time limit") from None
            raise DatabaseError("query could not be executed") from None
        except sqlite3.Error:
            raise DatabaseError("query could not be executed") from None
        finally:
            self._connection.set_progress_handler(None, 0)
        return QueryResult(columns=columns, rows=rows, truncated=False, message=None)

    def close(self) -> None:
        """Close the database connection."""
        self._connection.close()

    def __enter__(self) -> SQLiteAdapter:
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()
