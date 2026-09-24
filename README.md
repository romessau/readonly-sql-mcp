# readonly-sql-mcp

A read-only Model Context Protocol (MCP) server for exploring SQL databases safely. It
provides schema discovery and guarded querying without granting a client write access.

Version 0.1.0 supports SQLite. PostgreSQL support is planned for 0.2.0.

This project is not yet published to PyPI. Install it from a source checkout.

## Quickstart

Python 3.11 or newer is required.

```console
python -m venv .venv
. .venv/bin/activate
pip install -e .
readonly-sql-mcp --database examples/ecommerce.sqlite
```

The server uses standard input/output, so an MCP client normally starts it rather than a
terminal user. Use an absolute database path if the client changes the working directory.

## Client configuration

Desktop MCP hosts typically need an absolute command path:

```json
{
  "mcpServers": {
    "sql": {
      "command": "/absolute/path/to/.venv/bin/readonly-sql-mcp",
      "args": ["--database", "/absolute/path/to/examples/ecommerce.sqlite"]
    }
  }
}
```

Editor MCP settings can use the environment instead:

```json
{
  "mcpServers": {
    "sql": {
      "command": "readonly-sql-mcp",
      "env": {
        "MCP_SQLITE_PATH": "/absolute/path/to/examples/ecommerce.sqlite",
        "MCP_SQL_ROW_LIMIT": "500",
        "MCP_SQL_TIMEOUT_MS": "5000"
      }
    }
  }
}
```

See `examples/desktop_config.json` and `examples/editor_config.json`.

## Tools and resource

| Name | Purpose |
| --- | --- |
| `list_tables` | Lists user tables and views. Planner row estimates appear when available. |
| `describe_table(name)` | Returns columns, types, nullability, primary and foreign keys, and indexes. |
| `run_query(sql)` | Executes one validated read-only query and returns columns, rows, and truncation metadata. |
| `schema://overview` | Returns the full accessible schema as JSON. |

`--row-limit` defaults to 500 rows. `--timeout-ms` defaults to 5000 milliseconds.
Queries longer than 50,000 characters are rejected before parsing.

## Security model

Queries are parsed with sqlglot. The server accepts exactly one read-only statement: a
`SELECT`, including `UNION` / `INTERSECT` / `EXCEPT`, parenthesized queries, `VALUES`, and
read-only common table expressions. It rejects writes, DDL, `ATTACH` / `DETACH`, `PRAGMA`
statements, table-valued `pragma_*` relations (which otherwise leak the database file path),
`SELECT INTO`, and known dangerous functions such as `load_extension`, `readfile`, and
`writefile`. Semicolons inside string literals remain valid.

Validation is only the first barrier. SQLite is opened through a `mode=ro` URI, which is the
write barrier. `query_only` is re-enabled after each statement as a best-effort extra check;
it does not stop `ATTACH` and can be turned off with `PRAGMA` if that statement is allowed to
execute. The adapter therefore also refuses `ATTACH`, `DETACH`, and `PRAGMA` at execute time.
Results are fetched up to the configured cap plus one row so the response can state whether
truncation occurred. SQLite queries are interrupted through a progress handler when their
approximate time budget expires.

See [the security policy](docs/security.md) for the threat model and operational guidance.

## Limitations

- SQLite cannot provide cheap row counts unless `sqlite_stat1` exists, so counts are often
  `null`.
- SQLite timeout enforcement is approximate and cannot bound time spent inside every native
  operation.
- The dangerous-function denylist must evolve with databases and installed extensions.
- This release accepts SQLite syntax only and does not provide PostgreSQL connectivity.
- Read-only access does not prevent expensive reads or inference of sensitive stored data.

## Development

```console
pip install -e '.[dev]'
ruff check .
ruff format --check .
mypy --strict src
pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the contribution workflow.

## License

MIT
