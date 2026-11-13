-- GROUP BY gives one summary row per label. A median resists large outliers.
SELECT is_fraud,
       CASE WHEN is_fraud = 1 THEN 'Fraud' ELSE 'Non-fraud' END AS label,
       COUNT(*) AS transaction_count,
       SUM(amount) AS total_amount,
       ROUND(AVG(amount), 2) AS mean_amount,
       MEDIAN(amount) AS median_amount,
       QUANTILE_CONT(amount, 0.95) AS p95_amount
FROM transactions
GROUP BY is_fraud
ORDER BY is_fraud;
