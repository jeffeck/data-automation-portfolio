-- Same result, rewritten:
--   1. Aggregate once in a CTE instead of three correlated subqueries.
--   2. Sargable date range (>= / <) so the index on order_date can be used.
--   3. Filter to qualifying orders first, then join to items and customers.
WITH orders_2024 AS (
    SELECT order_id, customer_id
      FROM orders
     WHERE order_date >= '2024-01-01'
       AND order_date <  '2025-01-01'
       AND status IN ('shipped', 'delivered')
),
customer_totals AS (
    SELECT o.customer_id,
           SUM(oi.quantity * oi.unit_price) AS revenue_2024,
           COUNT(DISTINCT o.order_id)       AS orders_2024
      FROM orders_2024 o
      JOIN order_items oi ON oi.order_id = o.order_id
     GROUP BY o.customer_id
)
SELECT c.region,
       c.customer_id,
       c.email,
       t.revenue_2024,
       t.orders_2024
  FROM customer_totals t
  JOIN customers c ON c.customer_id = t.customer_id
 ORDER BY c.region, t.revenue_2024 DESC
 LIMIT 50;
