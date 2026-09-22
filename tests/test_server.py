from __future__ import annotations

import json
from pathlib import Path

import pytest
from mcp.server.fastmcp.exceptions import ResourceError, ToolError

from readonly_sql_mcp.config import Settings
from readonly_sql_mcp.db.sqlite import SQLiteAdapter
from readonly_sql_mcp.server import create_server


@pytest.mark.anyio
async def test_exposes_expected_tools(database_path: Path, adapter: SQLiteAdapter) -> None:
    server = create_server(Settings(database_path), adapter)
    tools = await server.list_tools()
    assert {tool.name for tool in tools} == {"list_tables", "describe_table", "run_query"}


@pytest.mark.anyio
async def test_run_query_validates_and_caps_rows(
    database_path: Path, adapter: SQLiteAdapter
) -> None:
    server = create_server(Settings(database_path, row_limit=1), adapter)
    _, result = await server.call_tool("run_query", {"sql": "SELECT * FROM customers ORDER BY id"})
    assert result["truncated"] is True
    assert result["rows"] == [[1, "Ada"]]


@pytest.mark.anyio
async def test_schema_resource_contains_descriptions(
    database_path: Path, adapter: SQLiteAdapter
) -> None:
    server = create_server(Settings(database_path), adapter)
    contents = await server.read_resource("schema://overview")
    document = json.loads(next(iter(contents)).content)
    assert {table["name"] for table in document["tables"]} == {
        "customers",
        "orders",
        "order_totals",
    }


@pytest.mark.anyio
async def test_query_tool_rejects_writes(database_path: Path, adapter: SQLiteAdapter) -> None:
    server = create_server(Settings(database_path), adapter)
    with pytest.raises(ToolError, match="SELECT"):
        await server.call_tool("run_query", {"sql": "DELETE FROM customers"})


@pytest.mark.anyio
async def test_describe_tool_has_safe_error(database_path: Path, adapter: SQLiteAdapter) -> None:
    server = create_server(Settings(database_path), adapter)
    with pytest.raises(ToolError, match="not found"):
        await server.call_tool("describe_table", {"name": "missing"})


@pytest.mark.anyio
async def test_schema_resource_sanitizes_database_errors(
    database_path: Path, adapter: SQLiteAdapter
) -> None:
    server = create_server(Settings(database_path), adapter)
    adapter.close()
    with pytest.raises(ResourceError, match="schema could not be read") as caught:
        await server.read_resource("schema://overview")
    assert caught.value.__cause__ is None
