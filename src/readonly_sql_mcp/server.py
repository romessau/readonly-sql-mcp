"""MCP schema tools."""

from __future__ import annotations

import sys
from typing import NoReturn

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from readonly_sql_mcp.config import Settings, parse_args
from readonly_sql_mcp.db.base import DatabaseAdapter, QueryResult, TableDescription, TableInfo
from readonly_sql_mcp.db.sqlite import DatabaseError, SQLiteAdapter
from readonly_sql_mcp.security import QueryValidationError, validate_query


def _tool_error(message: str) -> NoReturn:
    raise ToolError(message)


def create_server(settings: Settings, adapter: DatabaseAdapter | None = None) -> FastMCP:
    """Create an MCP server backed by the configured database."""
    database = adapter or SQLiteAdapter(settings.database_path, settings.query_timeout_ms)
    mcp = FastMCP("readonly-sql-mcp")

    @mcp.tool()
    def list_tables() -> list[TableInfo]:
        """List accessible tables and views."""
        try:
            return database.list_tables()
        except DatabaseError:
            _tool_error("database metadata could not be read")

    @mcp.tool()
    def describe_table(name: str) -> TableDescription:
        """Describe columns, keys, and indexes for a table or view."""
        try:
            return database.describe_table(name)
        except DatabaseError as exc:
            _tool_error(str(exc))

    @mcp.tool()
    def run_query(sql: str) -> QueryResult:
        """Run one validated SELECT statement."""
        try:
            return database.run_query(validate_query(sql), settings.row_limit)
        except (QueryValidationError, DatabaseError) as exc:
            _tool_error(str(exc))

    return mcp


def main() -> None:
    """Run the server over standard input and output."""
    try:
        settings = parse_args()
        create_server(settings).run(transport="stdio")
    except DatabaseError:
        print("unable to open database", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
