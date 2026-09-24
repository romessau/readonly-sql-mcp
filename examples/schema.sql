CREATE TABLE customers (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE
);

CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    price_cents INTEGER NOT NULL CHECK (price_cents >= 0)
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    ordered_at TEXT NOT NULL,
    status TEXT NOT NULL
);

CREATE TABLE order_items (
    order_id INTEGER NOT NULL REFERENCES orders(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    PRIMARY KEY (order_id, product_id)
);

CREATE INDEX orders_customer_idx ON orders(customer_id);

INSERT INTO customers VALUES
    (1, 'Ada Lovelace', 'ada@example.test'),
    (2, 'Grace Hopper', 'grace@example.test');
INSERT INTO products VALUES
    (1, 'Mechanical Keyboard', 12900),
    (2, 'USB-C Dock', 8900),
    (3, 'Notebook', 1200);
INSERT INTO orders VALUES
    (1, 1, '2026-01-15T10:30:00Z', 'shipped'),
    (2, 2, '2026-01-17T14:00:00Z', 'processing');
INSERT INTO order_items VALUES (1, 1, 1), (1, 3, 2), (2, 2, 1);

ANALYZE;

