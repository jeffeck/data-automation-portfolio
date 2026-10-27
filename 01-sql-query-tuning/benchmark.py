"""Time the original vs. tuned query and confirm they return identical results.

Usage: python setup_db.py && python benchmark.py
"""
import sqlite3
import time
from pathlib import Path

HERE = Path(__file__).parent
DB_PATH = HERE / "shop.db"


def run(con: sqlite3.Connection, sql: str) -> tuple[list, float]:
    start = time.perf_counter()
    rows = con.execute(sql).fetchall()
    return rows, time.perf_counter() - start


def plan(con: sqlite3.Connection, sql: str) -> str:
    return "\n".join("    " + row[-1] for row in con.execute("EXPLAIN QUERY PLAN " + sql))


def rounded(rows: list) -> list:
    return [tuple(round(v, 2) if isinstance(v, float) else v for v in r) for r in rows]


def main() -> None:
    if not DB_PATH.exists():
        raise SystemExit("shop.db not found. Run `python setup_db.py` first.")

    slow_sql = (HERE / "slow_query.sql").read_text()
    fast_sql = (HERE / "fast_query.sql").read_text()

    con = sqlite3.connect(DB_PATH)
    con.executescript("DROP INDEX IF EXISTS idx_orders_date_status; DROP INDEX IF EXISTS idx_order_items_order;")

    print("Original query plan:\n" + plan(con, slow_sql))
    slow_rows, slow_t = run(con, slow_sql)
    print(f"Original query: {slow_t:.2f}s\n")

    con.executescript((HERE / "indexes.sql").read_text())
    print("Tuned query plan:\n" + plan(con, fast_sql))
    fast_rows, fast_t = run(con, fast_sql)
    print(f"Tuned query:    {fast_t:.2f}s\n")

    assert rounded(slow_rows) == rounded(fast_rows), "Results differ!"
    print(f"Results identical ({len(fast_rows)} rows). Speedup: {slow_t / fast_t:.0f}x")


if __name__ == "__main__":
    main()
