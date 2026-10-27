"""Build a realistic sample SQLite database: customers, orders, order_items.

Usage: python setup_db.py [--customers 50000] [--orders 500000]
"""
import argparse
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "shop.db"
REGIONS = ["North", "South", "East", "West", "Central"]
STATUSES = ["pending", "shipped", "delivered", "cancelled", "returned"]


def build(customers: int, orders: int, seed: int = 42) -> None:
    random.seed(seed)
    DB_PATH.unlink(missing_ok=True)
    con = sqlite3.connect(DB_PATH)
    con.executescript(
        """
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            email       TEXT NOT NULL,
            region      TEXT NOT NULL,
            signup_date TEXT NOT NULL
        );
        CREATE TABLE orders (
            order_id    INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
            order_date  TEXT NOT NULL,
            status      TEXT NOT NULL
        );
        CREATE TABLE order_items (
            order_id   INTEGER NOT NULL REFERENCES orders(order_id),
            sku        TEXT NOT NULL,
            quantity   INTEGER NOT NULL,
            unit_price REAL NOT NULL
        );
        """
    )

    start = date(2022, 1, 1)
    con.executemany(
        "INSERT INTO customers VALUES (?, ?, ?, ?)",
        (
            (i, f"user{i}@example.com", random.choice(REGIONS),
             (start + timedelta(days=random.randint(0, 900))).isoformat())
            for i in range(1, customers + 1)
        ),
    )
    con.executemany(
        "INSERT INTO orders VALUES (?, ?, ?, ?)",
        (
            (i, random.randint(1, customers),
             (start + timedelta(days=random.randint(0, 1000))).isoformat(),
             random.choices(STATUSES, weights=[5, 10, 75, 7, 3])[0])
            for i in range(1, orders + 1)
        ),
    )
    con.executemany(
        "INSERT INTO order_items VALUES (?, ?, ?, ?)",
        (
            (order_id, f"SKU-{random.randint(1, 2000):04d}",
             random.randint(1, 5), round(random.uniform(5, 250), 2))
            for order_id in range(1, orders + 1)
            for _ in range(random.randint(1, 4))
        ),
    )
    con.commit()
    con.close()
    print(f"Built {DB_PATH.name}: {customers:,} customers, {orders:,} orders")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--customers", type=int, default=2_000)
    parser.add_argument("--orders", type=int, default=40_000)
    args = parser.parse_args()
    build(args.customers, args.orders)
