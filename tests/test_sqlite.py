import sqlite3
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
    assert description["columns"][0] == {
        "name": "id",
        "type": "INTEGER",
        "nullable": False,
        "primary_key": True,
    }
    assert description["foreign_keys"] == [
        {"column": "customer_id", "referenced_table": "customers", "referenced_column": "id"}
    ]
    assert description["indexes"] == [
        {"name": "orders_customer_idx", "unique": False, "columns": ["customer_id"]}
    ]


def test_rejects_unknown_table(adapter: SQLiteAdapter) -> None:
    with pytest.raises(DatabaseError, match="not found"):
        adapter.describe_table("unknown")


def test_caps_query_rows(adapter: SQLiteAdapter) -> None:
    result = adapter.run_query("SELECT id, name FROM customers ORDER BY id", 1)
    assert result == {
        "columns": ["id", "name"],
        "rows": [[1, "Ada"]],
        "truncated": True,
        "message": "Result truncated at 1 rows.",
    }


@pytest.mark.parametrize(
    ("sql", "limit", "row_count", "truncated"),
    [
        ("SELECT id FROM customers WHERE 0", 2, 0, False),
        ("SELECT id FROM customers ORDER BY id", 2, 2, False),
        ("SELECT id FROM orders ORDER BY id", 2, 2, True),
    ],
)
def test_row_cap_boundaries(
    adapter: SQLiteAdapter, sql: str, limit: int, row_count: int, truncated: bool
) -> None:
    result = adapter.run_query(sql, limit)
    assert len(result["rows"]) == row_count
    assert result["truncated"] is truncated
    assert (result["message"] is not None) is truncated


@pytest.mark.parametrize("limit", [0, -1])
def test_rejects_nonpositive_row_limit(adapter: SQLiteAdapter, limit: int) -> None:
    with pytest.raises(DatabaseError, match="positive"):
        adapter.run_query("SELECT 1", limit)


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


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT readfile('/private/secret')",
        "SELECT writefile('/tmp/readonly-sql-mcp-write', 'x')",
        "SELECT load_extension('missing')",
        "SELECT sqlite3_load_extension('missing')",
    ],
)
def test_adapter_sanitizes_dangerous_function_errors(adapter: SQLiteAdapter, sql: str) -> None:
    with pytest.raises(DatabaseError, match="could not be executed") as caught:
        adapter.run_query(sql, 10)
    assert "/private/secret" not in str(caught.value)


def test_reports_invalid_query_without_driver_details(adapter: SQLiteAdapter) -> None:
    with pytest.raises(DatabaseError, match="could not be executed"):
        adapter.run_query("SELECT * FROM missing", 10)


def test_metadata_errors_are_sanitized(adapter: SQLiteAdapter) -> None:
    adapter.close()
    with pytest.raises(DatabaseError, match="metadata could not be read") as list_error:
        adapter.list_tables()
    with pytest.raises(DatabaseError, match="metadata could not be read") as describe_error:
        adapter.describe_table("customers")
    assert list_error.value.__cause__ is None
    assert describe_error.value.__cause__ is None


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


@pytest.mark.parametrize("contents", [b"", b"not a sqlite database"])
def test_rejects_non_sqlite_files_without_leaking_path(tmp_path: Path, contents: bytes) -> None:
    path = tmp_path / "private-name.sqlite"
    path.write_bytes(contents)
    with pytest.raises(DatabaseError, match="unable to open database") as caught:
        SQLiteAdapter(path)
    assert str(path) not in str(caught.value)


def test_uses_maximum_statistical_estimate(tmp_path: Path) -> None:
    path = tmp_path / "statistics.sqlite"
    connection = sqlite3.connect(path)
    connection.executescript(
        "CREATE TABLE items(a INTEGER, b INTEGER);"
        "CREATE INDEX items_a ON items(a);"
        "CREATE INDEX items_b ON items(b);"
        "INSERT INTO items VALUES (1, 1), (2, 2), (3, 3);"
        "ANALYZE;"
        "UPDATE sqlite_stat1 SET stat = '5 1' WHERE idx = 'items_a';"
        "UPDATE sqlite_stat1 SET stat = '9 1' WHERE idx = 'items_b';"
    )
    connection.commit()
    connection.close()
    with SQLiteAdapter(path) as opened:
        assert opened.list_tables() == [{"name": "items", "type": "table", "row_count": 9}]
