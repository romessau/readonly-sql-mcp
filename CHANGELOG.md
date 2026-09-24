# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-09-24

### Added

- Read-only SQLite adapter with table, view, column, key, and index introspection.
- MCP tools for listing tables, describing objects, and running guarded queries.
- `schema://overview` resource containing the accessible schema.
- sqlglot-based single-`SELECT` validation and dangerous-function blocking.
- Configurable row cap with explicit truncation metadata.
- Approximate SQLite query timeout using a progress handler.
- Synthetic commerce database, client configuration examples, and security documentation.
- Ruff, strict mypy, pytest coverage, pre-commit, and continuous-integration checks.
