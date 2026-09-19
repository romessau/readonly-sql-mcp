from __future__ import annotations

from pathlib import Path

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from readonly_sql_mcp.config import Settings
from readonly_sql_mcp.db.sqlite import SQLiteAdapter
from readonly_sql_mcp.server import create_server


@pytest.mark.anyio
async def test_exposes_schema_tools(database_path: Path, adapter: SQLiteAdapter) -> None:
    server = create_server(Settings(database_path), adapter)
    tools = await server.list_tools()
    assert {tool.name for tool in tools} == {"list_tables", "describe_table", "run_query"}


@pytest.mark.anyio
async def test_calls_schema_and_query_tools(database_path: Path, adapter: SQLiteAdapter) -> None:
    server = create_server(Settings(database_path), adapter)
    _, tables = await server.call_tool("list_tables", {})
    _, result = await server.call_tool("run_query", {"sql": "SELECT 1 AS value"})
    assert tables
    assert result["rows"] == [[1]]


@pytest.mark.anyio
async def test_describe_tool_has_safe_error(database_path: Path, adapter: SQLiteAdapter) -> None:
    server = create_server(Settings(database_path), adapter)
    with pytest.raises(ToolError, match="not found"):
        await server.call_tool("describe_table", {"name": "missing"})


@pytest.mark.anyio
async def test_query_tool_rejects_writes(database_path: Path, adapter: SQLiteAdapter) -> None:
    server = create_server(Settings(database_path), adapter)
    with pytest.raises(ToolError, match="SELECT"):
        await server.call_tool("run_query", {"sql": "DELETE FROM customers"})
