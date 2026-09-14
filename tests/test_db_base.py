from readonly_sql_mcp.db import base


def test_defines_database_contracts() -> None:
    assert set(base.TableInfo.__annotations__) == {"name", "type", "row_count"}
    assert {"list_tables", "describe_table", "run_query", "close"} <= set(
        base.DatabaseAdapter.__dict__
    )
