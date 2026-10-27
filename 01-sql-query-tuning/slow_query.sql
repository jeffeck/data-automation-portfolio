-- "Top customers by 2024 revenue in each region" -- as it was originally written.
-- Problems:
--   1. Correlated subqueries re-scan orders/order_items once per customer.
--   2. strftime() on order_date prevents any index from being used.
--   3. No indexes on the foreign keys.
SELECT
    c.region,
    c.customer_id,
    c.email,
    (SELECT SUM(oi.quantity * oi.unit_price)
       FROM orders o
       JOIN order_items oi ON oi.order_id = o.order_id
      WHERE o.customer_id = c.customer_id
        AND strftime('%Y', o.order_date) = '2024'
        AND o.status IN ('shipped', 'delivered')) AS revenue_2024,
    (SELECT COUNT(*)
       FROM orders o
      WHERE o.customer_id = c.customer_id
        AND strftime('%Y', o.order_date) = '2024'
        AND o.status IN ('shipped', 'delivered')) AS orders_2024
FROM customers c
WHERE (SELECT COUNT(*)
         FROM orders o
        WHERE o.customer_id = c.customer_id
          AND strftime('%Y', o.order_date) = '2024'
          AND o.status IN ('shipped', 'delivered')) > 0
ORDER BY c.region, revenue_2024 DESC
LIMIT 50;
