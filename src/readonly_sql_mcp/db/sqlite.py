"""Read-only SQLite adapter."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from readonly_sql_mcp.db.base import (
    ColumnInfo,
    ForeignKeyInfo,
    IndexInfo,
    QueryResult,
    TableDescription,
    TableInfo,
)


class DatabaseError(Exception):
    """A safe database error suitable for returning to clients."""


class QueryTimeoutError(DatabaseError):
    """The database stopped a query after its configured time budget."""


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


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

    def list_tables(self) -> list[TableInfo]:
        """List user tables and views with available planner estimates."""
        objects = self._connection.execute(
            "SELECT name, type FROM sqlite_schema "
            "WHERE type IN ('table', 'view') AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
        estimates: dict[str, int] = {}
        has_stats = self._connection.execute(
            "SELECT 1 FROM sqlite_schema WHERE type = 'table' AND name = 'sqlite_stat1'"
        ).fetchone()
        if has_stats:
            for row in self._connection.execute("SELECT tbl, stat FROM sqlite_stat1"):
                first = str(row["stat"]).split()[0]
                if first.isdigit():
                    estimates[str(row["tbl"])] = int(first)
        return [
            TableInfo(
                name=str(row["name"]),
                type=str(row["type"]),
                row_count=estimates.get(str(row["name"])),
            )
            for row in objects
        ]

    def describe_table(self, name: str) -> TableDescription:
        """Return columns, foreign keys, and indexes for a table or view."""
        found = self._connection.execute(
            "SELECT 1 FROM sqlite_schema "
            "WHERE name = ? AND type IN ('table', 'view') AND name NOT LIKE 'sqlite_%'",
            (name,),
        ).fetchone()
        if found is None:
            raise DatabaseError("table or view not found")
        quoted = _quote_identifier(name)
        columns: list[ColumnInfo] = [
            ColumnInfo(
                name=str(row["name"]),
                type=str(row["type"]),
                nullable=not bool(row["notnull"]) and not bool(row["pk"]),
                primary_key=bool(row["pk"]),
            )
            for row in self._connection.execute(f"PRAGMA table_info({quoted})")
        ]
        foreign_keys: list[ForeignKeyInfo] = [
            ForeignKeyInfo(
                column=str(row["from"]),
                referenced_table=str(row["table"]),
                referenced_column=str(row["to"]),
            )
            for row in self._connection.execute(f"PRAGMA foreign_key_list({quoted})")
        ]
        indexes: list[IndexInfo] = []
        for row in self._connection.execute(f"PRAGMA index_list({quoted})"):
            index_name = str(row["name"])
            index_columns = [
                str(column["name"])
                for column in self._connection.execute(
                    f"PRAGMA index_info({_quote_identifier(index_name)})"
                )
            ]
            indexes.append(
                IndexInfo(name=index_name, unique=bool(row["unique"]), columns=index_columns)
            )
        return TableDescription(
            name=name, columns=columns, foreign_keys=foreign_keys, indexes=indexes
        )

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
