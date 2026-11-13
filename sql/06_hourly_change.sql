-- A recursive CTE fills empty hours, then LAG compares with the preceding hour.
WITH RECURSIVE hours(elapsed_hour) AS (
    SELECT MIN(elapsed_hour) FROM transactions
    UNION ALL
    SELECT elapsed_hour + 1 FROM hours
    WHERE elapsed_hour < (SELECT MAX(elapsed_hour) FROM transactions)
), hourly AS (
    SELECT hours.elapsed_hour, COUNT(t.transaction_id) AS transaction_count
    FROM hours LEFT JOIN transactions t USING (elapsed_hour)
    GROUP BY hours.elapsed_hour
), changes AS (
    SELECT *, LAG(transaction_count) OVER (ORDER BY elapsed_hour) AS previous_count
    FROM hourly
)
SELECT *, ROUND(100.0 * (transaction_count - previous_count) / NULLIF(previous_count, 0), 2)
          AS change_pct
FROM changes ORDER BY elapsed_hour;
