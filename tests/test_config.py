from __future__ import annotations

from pathlib import Path

import pytest

from readonly_sql_mcp.config import Settings, parse_args


def test_loads_settings_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MCP_SQLITE_PATH", "/tmp/example.sqlite")
    monkeypatch.setenv("MCP_SQL_ROW_LIMIT", "25")
    monkeypatch.setenv("MCP_SQL_TIMEOUT_MS", "800")
    assert Settings.from_env() == Settings(Path("/tmp/example.sqlite"), 25, 800)


def test_environment_requires_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MCP_SQLITE_PATH", raising=False)
    with pytest.raises(ValueError, match="required"):
        Settings.from_env()


@pytest.mark.parametrize("field", ["row_limit", "query_timeout_ms"])
def test_rejects_nonpositive_limits(field: str) -> None:
    with pytest.raises(ValueError, match="positive"):
        if field == "row_limit":
            Settings(database_path=Path("db.sqlite"), row_limit=0)
        else:
            Settings(database_path=Path("db.sqlite"), query_timeout_ms=0)


def test_parses_cli_arguments() -> None:
    arguments = ["--database", "shop.sqlite", "--row-limit", "12", "--timeout-ms", "90"]
    assert parse_args(arguments) == Settings(Path("shop.sqlite"), 12, 90)


def test_cli_requires_database(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MCP_SQLITE_PATH", raising=False)
    with pytest.raises(SystemExit):
        parse_args([])
