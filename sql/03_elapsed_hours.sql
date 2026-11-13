-- These are hours since the first transaction, NOT local hours of the day.
SELECT elapsed_hour,
       COUNT(*) AS transaction_count,
       SUM(is_fraud) AS fraud_count,
       ROUND(100.0 * AVG(is_fraud), 6) AS fraud_rate_pct,
       SUM(amount) AS total_amount
FROM transactions
GROUP BY elapsed_hour
ORDER BY elapsed_hour;
