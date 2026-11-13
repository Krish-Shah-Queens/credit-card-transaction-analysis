-- An educational rule: flag every amount >= a threshold. This is NOT a trained model.
-- Precision = labeled fraud among alerts; recall = labeled fraud captured / all labeled fraud.
-- NULLIF returns NULL when a metric has no denominator (for example, no alerts).
WITH thresholds(threshold_amount) AS (VALUES (100), (500), (1000)), counts AS (
    SELECT threshold_amount,
           COUNT(*) FILTER (WHERE amount >= threshold_amount) AS alert_count,
           COUNT(*) FILTER (WHERE amount >= threshold_amount AND is_fraud = 1) AS true_positives,
           SUM(is_fraud) AS total_fraud,
           COUNT(*) AS total_transactions
    FROM transactions CROSS JOIN thresholds
    GROUP BY threshold_amount
)
SELECT *, alert_count - true_positives AS false_positives,
       total_fraud - true_positives AS false_negatives,
       ROUND(100.0 * true_positives / NULLIF(alert_count, 0), 4) AS precision_pct,
       ROUND(100.0 * true_positives / NULLIF(total_fraud, 0), 4) AS recall_pct,
       ROUND(100.0 * alert_count / total_transactions, 4) AS alert_rate_pct
FROM counts ORDER BY threshold_amount;
