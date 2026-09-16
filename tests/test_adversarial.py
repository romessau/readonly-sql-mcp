import pytest

from readonly_sql_mcp.db.sqlite import DatabaseError, SQLiteAdapter


@pytest.mark.parametrize(
    "sql",
    [
        "INSERT INTO customers VALUES (3, 'Edsger')",
        "UPDATE customers SET name = 'x'",
        "DELETE FROM customers",
        "CREATE TABLE backup(id INTEGER)",
        "DROP TABLE customers",
        "ALTER TABLE customers RENAME TO people",
    ],
)
def test_native_read_only_mode_rejects_mutation(adapter: SQLiteAdapter, sql: str) -> None:
    with pytest.raises(DatabaseError, match="could not be executed") as caught:
        adapter.run_query(sql, 10)
    assert caught.value.__cause__ is None


def test_driver_errors_do_not_echo_query(adapter: SQLiteAdapter) -> None:
    secret = "private_relation_name"
    with pytest.raises(DatabaseError, match="could not be executed") as caught:
        adapter.run_query(f"SELECT * FROM {secret}", 10)
    assert secret not in str(caught.value)
