# SQL Query Tuning: 257x Faster, Same Results

A common request: *"This report query takes forever. Can you make it fast?"*

The query finds the top customers by 2024 revenue in each region. The original version works, but it slows down sharply as the data grows.

## Results

| | Runtime | Plan |
|---|---|---|
| Original | 7.08 s | Full scan of `orders` three times per customer |
| Tuned | 0.03 s | One index range scan, one aggregation |

These numbers come from running `benchmark.py` on 2,000 customers and 40,000 orders. The gap keeps growing as the tables get bigger. `benchmark.py` checks that both queries return identical rows.

## What was wrong

1. **Correlated subqueries.** Three subqueries re-scan `orders` for every customer, so the work grows with customers × orders.
2. **Non-sargable filter.** `strftime('%Y', order_date) = '2024'` wraps the column in a function, so no index can be used.
3. **Missing indexes** on the columns used for joins and filters.

## The fix

- **Aggregate once.** The tuned query filters 2024 orders in a CTE, joins to the line items, groups by customer, and then joins to `customers`.
- **Use a range filter.** `order_date >= '2024-01-01' AND order_date < '2025-01-01'` lets the database use an index.
- **Add a covering index.** `orders (order_date, status, customer_id)` answers the filter without touching the table, and a separate index covers `order_items.order_id`.

Compare `slow_query.sql` with `fast_query.sql`, and see `indexes.sql` for the indexes.

## Run it

```bash
python setup_db.py      # builds shop.db with realistic sample data
python benchmark.py     # prints both query plans, timings, and verifies results match
```

This demo uses SQLite so it runs with no setup. The same techniques apply to PostgreSQL, MySQL, and SQL Server, where you'd read `EXPLAIN ANALYZE` or the execution plan instead.
