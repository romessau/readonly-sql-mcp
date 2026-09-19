import pytest

from readonly_sql_mcp.security import MAX_QUERY_LENGTH, QueryValidationError, validate_query


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1; DROP TABLE customers",
        "SELECT 1/**/;/**/DELETE FROM customers",
        " SELECT 1 ; -- hidden statement\n DELETE FROM customers",
        "DELETE FROM customers",
        "INSERT INTO customers(name) VALUES ('Edsger')",
        "UPDATE customers SET name = 'x'",
        "WITH chosen AS (SELECT 1) DELETE FROM customers",
        "WITH removed AS (DELETE FROM customers RETURNING id) SELECT * FROM removed",
        "PRAGMA table_info(customers)",
        "ATTACH DATABASE '/tmp/other.db' AS other",
        "COPY customers TO '/tmp/customers.csv'",
        "SELECT * INTO backup FROM customers",
        "CREATE TABLE backup(id INTEGER)",
        "DROP TABLE customers",
        "ALTER TABLE customers RENAME TO people",
        "DETACH DATABASE other",
        "BEGIN TRANSACTION",
    ],
)
def test_rejects_non_read_only_statements(sql: str) -> None:
    with pytest.raises(QueryValidationError):
        validate_query(sql)


@pytest.mark.parametrize(
    "function_name",
    [
        "load_extension",
        "readfile",
        "writefile",
        "sqlite3_load_extension",
        "sqlite_load_extension",
    ],
)
def test_rejects_dangerous_functions(function_name: str) -> None:
    with pytest.raises(QueryValidationError, match="function"):
        validate_query(f"SELECT {function_name}('argument')")


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT * FROM pragma_database_list",
        "SELECT * FROM pragma_compile_options",
        "SELECT * FROM pragma_table_list",
        "SELECT * FROM pragma_query_only",
        "SELECT * FROM pragma_journal_mode",
        'SELECT * FROM "pragma_database_list"',
        "SELECT * FROM [pragma_database_list]",
        "WITH exposed AS (SELECT * FROM pragma_database_list) SELECT * FROM exposed",
        "SELECT * FROM pragma_table_info",
        "SELECT * FROM pragma_table_info('customers')",
    ],
)
def test_rejects_pragma_relations(sql: str) -> None:
    with pytest.raises(QueryValidationError, match="forbidden operation"):
        validate_query(sql)


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1",
        "  SeLeCt 1  ",
        "WITH values_cte AS (SELECT 1 AS value) SELECT value FROM values_cte",
        "SELECT ';' AS punctuation",
        "SELECT 'not; a; statement' AS text",
        "SELECT 1; -- one trailing delimiter is valid",
        "SELECT 'DELETE FROM customers' AS harmless_text",
        "SELECT 1 UNION SELECT 2",
        "SELECT 1 UNION ALL SELECT 2",
        "SELECT 1 INTERSECT SELECT 1",
        "SELECT 1 EXCEPT SELECT 2",
        "VALUES (1), (2)",
        "(SELECT 1)",
        "SELECT COUNT(*) FROM customers",
    ],
)
def test_accepts_single_select_queries(sql: str) -> None:
    assert validate_query(sql) == sql.strip()


def test_rejects_empty_input() -> None:
    with pytest.raises(QueryValidationError, match="exactly one"):
        validate_query(" -- only a comment")


def test_rejects_oversized_query_before_parsing() -> None:
    oversized = "SELECT 1 /*" + "x" * MAX_QUERY_LENGTH + "*/"
    with pytest.raises(QueryValidationError, match="maximum length"):
        validate_query(oversized)


def test_errors_do_not_echo_sql() -> None:
    secret = "private-secret"
    with pytest.raises(QueryValidationError) as caught:
        validate_query(f"DELETE FROM {secret}")
    assert secret not in str(caught.value)


def test_rejects_wrapped_write() -> None:
    with pytest.raises(QueryValidationError):
        validate_query("(DELETE FROM customers RETURNING id)")
