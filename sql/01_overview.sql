-- COUNT counts transactions; SUM adds amounts; AVG computes the mean.
-- A binary label's average is its rate. Multiply by 100 for a percentage.
SELECT COUNT(*) AS transaction_count,
       SUM(is_fraud) AS fraud_count,
       ROUND(100.0 * AVG(is_fraud), 6) AS fraud_rate_pct,
       SUM(amount) AS total_amount,
       ROUND(AVG(amount), 2) AS mean_amount,
       MEDIAN(amount) AS median_amount,
       MAX(amount) AS maximum_amount,
       MIN(elapsed_seconds) AS first_elapsed_second,
       MAX(elapsed_seconds) AS last_elapsed_second
FROM transactions;
