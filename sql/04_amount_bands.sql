-- CASE creates readable groups; a CTE gives the grouped input a name.
-- Intervals are [lower, upper), except the last which has no upper bound.
WITH banded AS (
    SELECT *, CASE WHEN amount < 10 THEN 1 WHEN amount < 50 THEN 2
                   WHEN amount < 100 THEN 3 WHEN amount < 500 THEN 4 ELSE 5 END AS band_order,
           CASE WHEN amount < 10 THEN '0 to <10' WHEN amount < 50 THEN '10 to <50'
                WHEN amount < 100 THEN '50 to <100' WHEN amount < 500 THEN '100 to <500'
                ELSE '500+' END AS amount_band
    FROM transactions
)
SELECT band_order, amount_band, COUNT(*) AS transaction_count,
       SUM(is_fraud) AS fraud_count,
       ROUND(100.0 * AVG(is_fraud), 6) AS fraud_rate_pct,
       SUM(amount) AS total_amount
FROM banded
GROUP BY band_order, amount_band
ORDER BY band_order;
