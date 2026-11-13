-- NTILE splits rows into ten almost equal-sized groups, largest amounts first.
-- transaction_id breaks ties; it is a local row key, not a source identifier.
WITH ranked AS (
    SELECT *, NTILE(10) OVER (ORDER BY amount DESC, transaction_id) AS amount_decile
    FROM transactions
), totals AS (
    SELECT amount_decile, COUNT(*) AS transaction_count,
           SUM(amount) AS total_amount, SUM(is_fraud) AS fraud_count
    FROM ranked GROUP BY amount_decile
)
SELECT *, ROUND(100.0 * total_amount / NULLIF(SUM(total_amount) OVER (), 0), 4)
           AS share_of_total_amount_pct
FROM totals
ORDER BY amount_decile;
