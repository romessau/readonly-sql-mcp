from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from pathlib import Path

import pytest

from readonly_sql_mcp.db.sqlite import SQLiteAdapter


@pytest.fixture
def database_path(tmp_path: Path) -> Path:
    path = tmp_path / "shop.sqlite"
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE customers (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL REFERENCES customers(id),
            total REAL NOT NULL
        );
        CREATE INDEX orders_customer_idx ON orders(customer_id);
        CREATE VIEW order_totals AS SELECT customer_id, SUM(total) AS total FROM orders
            GROUP BY customer_id;
        INSERT INTO customers VALUES (1, 'Ada'), (2, 'Grace');
        INSERT INTO orders VALUES (1, 1, 12.5), (2, 1, 9.0), (3, 2, 20.0);
        """
    )
    connection.close()
    return path


@pytest.fixture
def adapter(database_path: Path) -> Iterator[SQLiteAdapter]:
    with SQLiteAdapter(database_path) as opened:
        yield opened
