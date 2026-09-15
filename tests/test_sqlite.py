from pathlib import Path

import pytest

from readonly_sql_mcp.db.sqlite import DatabaseError, QueryTimeoutError, SQLiteAdapter


def test_requires_existing_database(tmp_path: Path) -> None:
    with pytest.raises(DatabaseError, match="does not exist"):
        SQLiteAdapter(tmp_path / "missing.sqlite")


def test_runs_read_query(adapter: SQLiteAdapter) -> None:
    result = adapter.run_query("SELECT id, name FROM customers ORDER BY id", 1)
    assert result["columns"] == ["id", "name"]
    assert result["rows"] == [[1, "Ada"], [2, "Grace"]]
    assert result["truncated"] is False


def test_database_is_read_only(adapter: SQLiteAdapter) -> None:
    with pytest.raises(DatabaseError, match="could not be executed"):
        adapter.run_query("DELETE FROM customers", 10)


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
