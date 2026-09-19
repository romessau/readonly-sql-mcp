from pathlib import Path

import pytest

from readonly_sql_mcp.db.sqlite import DatabaseError, QueryTimeoutError, SQLiteAdapter


def test_requires_existing_database(tmp_path: Path) -> None:
    with pytest.raises(DatabaseError, match="does not exist"):
        SQLiteAdapter(tmp_path / "missing.sqlite")


def test_lists_tables_and_views(adapter: SQLiteAdapter) -> None:
    assert adapter.list_tables() == [
        {"name": "customers", "type": "table", "row_count": None},
        {"name": "order_totals", "type": "view", "row_count": None},
        {"name": "orders", "type": "table", "row_count": None},
    ]


def test_describes_table(adapter: SQLiteAdapter) -> None:
    description = adapter.describe_table("orders")
    assert description["columns"][0]["name"] == "id"
    assert description["foreign_keys"] == [
        {"column": "customer_id", "referenced_table": "customers", "referenced_column": "id"}
    ]
    assert description["indexes"] == [
        {"name": "orders_customer_idx", "unique": False, "columns": ["customer_id"]}
    ]


def test_rejects_unknown_table(adapter: SQLiteAdapter) -> None:
    with pytest.raises(DatabaseError, match="not found"):
        adapter.describe_table("unknown")


def test_runs_read_query(adapter: SQLiteAdapter) -> None:
    result = adapter.run_query("SELECT id, name FROM customers ORDER BY id", 1)
    assert result["columns"] == ["id", "name"]
    assert result["rows"] == [[1, "Ada"], [2, "Grace"]]
    assert result["truncated"] is False


def test_database_is_read_only(adapter: SQLiteAdapter) -> None:
    with pytest.raises(DatabaseError, match="could not be executed"):
        adapter.run_query("DELETE FROM customers", 10)


@pytest.mark.parametrize(
    "sql",
    [
        "ATTACH DATABASE '/tmp/readonly-sql-mcp-other.sqlite' AS other",
        "DETACH DATABASE main",
        "PRAGMA query_only=OFF",
        "PRAGMA writable_schema=ON",
        "/* leading comment */ ATTACH DATABASE '/tmp/readonly-sql-mcp-other.sqlite' AS other",
    ],
)
def test_adapter_rejects_connection_escapes(adapter: SQLiteAdapter, sql: str) -> None:
    with pytest.raises(DatabaseError, match="could not be executed"):
        adapter.run_query(sql, 10)


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM pragma_database_list",
        'SELECT * FROM "pragma_database_list"',
        "WITH exposed AS (SELECT * FROM pragma_database_list) SELECT * FROM exposed",
        "SELECT * FROM (SELECT * FROM pragma_database_list)",
        "SELECT * FROM pragma_table_info('customers')",
    ],
)
def test_adapter_rejects_pragma_relations(adapter: SQLiteAdapter, sql: str) -> None:
    with pytest.raises(DatabaseError, match="could not be executed"):
        adapter.run_query(sql, 10)


def test_adapter_reasserts_query_only(adapter: SQLiteAdapter) -> None:
    adapter.run_query("SELECT 1", 10)
    value = adapter._connection.execute("PRAGMA query_only").fetchone()[0]
    assert value == 1


def test_metadata_errors_are_sanitized(adapter: SQLiteAdapter) -> None:
    adapter.close()
    with pytest.raises(DatabaseError, match="metadata could not be read") as list_error:
        adapter.list_tables()
    with pytest.raises(DatabaseError, match="metadata could not be read") as describe_error:
        adapter.describe_table("customers")
    assert list_error.value.__cause__ is None
    assert describe_error.value.__cause__ is None


@pytest.mark.parametrize("contents", [b"", b"not a sqlite database"])
def test_rejects_non_sqlite_files_without_leaking_path(tmp_path: Path, contents: bytes) -> None:
    path = tmp_path / "private-name.sqlite"
    path.write_bytes(contents)
    with pytest.raises(DatabaseError, match="unable to open database") as caught:
        SQLiteAdapter(path)
    assert str(path) not in str(caught.value)


def test_interrupts_expensive_query(database_path: Path) -> None:
    query = """
        WITH RECURSIVE numbers(value) AS (
            SELECT 1 UNION ALL SELECT value + 1 FROM numbers WHERE value < 100000000
        ) SELECT SUM(value) FROM numbers
    """
    with (
        SQLiteAdapter(database_path, timeout_ms=1) as adapter,
        pytest.raises(QueryTimeoutError, match="time limit"),
    ):
        adapter.run_query(query, 10)
