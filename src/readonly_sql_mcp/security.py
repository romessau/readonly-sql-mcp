"""AST-based query validation."""

from __future__ import annotations

from sqlglot import exp, parse
from sqlglot.errors import ParseError


class QueryValidationError(ValueError):
    """SQL does not meet the server's read-only policy."""


_FORBIDDEN_NODES = (
    exp.Attach,
    exp.Command,
    exp.Copy,
    exp.Delete,
    exp.Insert,
    exp.Into,
    exp.Merge,
    exp.Pragma,
    exp.Update,
)


def _function_name(node: exp.Func) -> str:
    if isinstance(node, exp.Anonymous):
        return node.name.lower()
    return node.key.lower()


def validate_query(sql: str, dialect: str = "sqlite") -> str:
    """Require exactly one SELECT and reject dangerous AST constructs."""
    candidate = sql.strip()
    try:
        statements = [
            statement
            for statement in parse(candidate, read=dialect)
            if statement and not isinstance(statement, exp.Semicolon)
        ]
    except (ParseError, ValueError) as exc:
        raise QueryValidationError("query is not valid SQL") from exc
    if len(statements) != 1:
        raise QueryValidationError("query must contain exactly one statement")

    statement = statements[0]
    if not isinstance(statement, exp.Select):
        raise QueryValidationError("query must be a SELECT statement")
    if any(statement.find(node_type) is not None for node_type in _FORBIDDEN_NODES):
        raise QueryValidationError("query contains a forbidden operation")
    if any(
        _function_name(function) == "load_extension" for function in statement.find_all(exp.Func)
    ):
        raise QueryValidationError("query calls a forbidden function")
    return candidate
