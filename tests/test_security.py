import pytest

from readonly_sql_mcp.security import QueryValidationError, validate_query


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1; DROP TABLE customers",
        "DELETE FROM customers",
        "INSERT INTO customers(name) VALUES ('Edsger')",
        "UPDATE customers SET name = 'x'",
        "WITH chosen AS (SELECT 1) DELETE FROM customers",
        "PRAGMA table_info(customers)",
        "ATTACH DATABASE '/tmp/other.db' AS other",
        "SELECT * INTO backup FROM customers",
    ],
)
def test_rejects_non_read_only_statements(sql: str) -> None:
    with pytest.raises(QueryValidationError):
        validate_query(sql)


def test_rejects_extension_loading() -> None:
    with pytest.raises(QueryValidationError, match="function"):
        validate_query("SELECT load_extension('argument')")


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1",
        "  SeLeCt 1  ",
        "WITH values_cte AS (SELECT 1 AS value) SELECT value FROM values_cte",
        "SELECT ';' AS punctuation",
        "SELECT COUNT(*) FROM customers",
    ],
)
def test_accepts_single_select_queries(sql: str) -> None:
    assert validate_query(sql) == sql.strip()


def test_rejects_empty_input() -> None:
    with pytest.raises(QueryValidationError, match="exactly one"):
        validate_query(" -- only a comment")


def test_errors_do_not_echo_sql() -> None:
    secret = "private-secret"
    with pytest.raises(QueryValidationError) as caught:
        validate_query(f"DELETE FROM {secret}")
    assert secret not in str(caught.value)
