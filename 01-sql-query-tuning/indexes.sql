-- Supporting indexes for the rewritten query.
CREATE INDEX IF NOT EXISTS idx_orders_date_status ON orders (order_date, status, customer_id);
CREATE INDEX IF NOT EXISTS idx_order_items_order  ON order_items (order_id);
ANALYZE;
