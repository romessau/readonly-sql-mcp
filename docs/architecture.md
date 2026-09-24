# Architecture

```text
MCP client
    │ tools and schema://overview
    ▼
FastMCP surface (server.py)
    │ validated SELECT
    ▼
AST policy (security.py) ── rejects commands, writes, and dangerous functions
    │
    ▼
DatabaseAdapter protocol
    │
    └── SQLiteAdapter ── mode=ro, query_only, progress timeout, row cap
```

## Boundaries

`server.py` owns protocol declarations and converts internal failures into safe client errors.
It contains no database metadata logic. `security.py` owns the shared statement policy. Adapter
implementations own native connection hardening, introspection, interruption, and conversion to
JSON-compatible result shapes.

## Decisions

### Read-only by construction

An exploratory server does not need mutation privileges. Rejecting writes reduces accidental
damage and narrows the impact of prompt injection, but validation bugs remain possible. Native
read-only connection settings therefore enforce the same boundary independently.

### sqlglot instead of regular expressions

SQL contains comments, quoted strings, nested expressions, and dialect syntax. A regular
expression cannot reliably distinguish a delimiter in a string from stacked statements or find
a write hidden behind a common table expression. sqlglot supplies a traversable syntax tree and
explicit statement boundaries.

### Native drivers instead of SQLAlchemy

The required defenses are driver-specific: SQLite read-only URI mode and progress callbacks now,
and PostgreSQL session settings in the next milestone. Native drivers expose these features
directly and avoid an abstraction that would add little value to a deliberately small adapter
interface.

### Bounded materialization

Adapters fetch at most the configured row cap plus one record. The extra record establishes
whether the response was truncated without reading the remainder of the result set.

