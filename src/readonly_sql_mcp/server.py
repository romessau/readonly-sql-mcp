"""MCP schema tools."""

from __future__ import annotations

from typing import NoReturn

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from readonly_sql_mcp.config import Settings
from readonly_sql_mcp.db.base import DatabaseAdapter, TableDescription, TableInfo
from readonly_sql_mcp.db.sqlite import DatabaseError, SQLiteAdapter


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

    return mcp
