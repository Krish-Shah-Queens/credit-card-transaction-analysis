# Practice SQL and Python

Run queries in the notebook connection `con`, or use the Python snippet in the README. Try each question before reading its answer.

## 1. Count labels

Return the number of rows for each fraud label. Does the fraud count alone tell you how common fraud is?

<details><summary>Solution</summary>

```sql
SELECT is_fraud, COUNT(*) AS rows
FROM transactions GROUP BY is_fraud ORDER BY is_fraud;
```

Expect 284,315 non-fraud rows and 492 fraud rows. Divide 492 by 284,807 and multiply by 100: about 0.1727%. Counts need a denominator.

</details>

## 2. Find amounts at least 1,000

Return the transaction count and fraud count for amounts at least 1,000. Use `WHERE`, then calculate the rate in Python.

<details><summary>Solution</summary>

```sql
SELECT COUNT(*) AS rows, SUM(is_fraud) AS frauds
FROM transactions WHERE amount >= 1000;
```

```python
result = con.execute("SELECT COUNT(*) AS rows, SUM(is_fraud) AS frauds FROM transactions WHERE amount >= 1000").fetchdf()
100 * result.loc[0, "frauds"] / result.loc[0, "rows"]
```

Compare with threshold 1000 in `07_threshold_tradeoffs.csv`. This subset rate is the rule's precision, not its recall.

</details>

## 3. Compare mean and median

Compute both for each label. Explain why they differ without assuming a cause for fraud.

<details><summary>Solution</summary>

```sql
SELECT is_fraud, AVG(amount) AS mean_amount, MEDIAN(amount) AS median_amount
FROM transactions GROUP BY is_fraud ORDER BY is_fraud;
```

Large transactions raise the mean more than the median. Inspect `02_class_summary.sql`. A difference between groups does not establish that amount causes fraud.

</details>

## 4. Require a minimum group size

Find elapsed hours with at least 1,000 transactions, ordering by fraud rate descending. Why does group size matter?

<details><summary>Solution</summary>

```sql
SELECT elapsed_hour, COUNT(*) AS rows, SUM(is_fraud) AS frauds,
       100.0 * AVG(is_fraud) AS fraud_rate_pct
FROM transactions GROUP BY elapsed_hour HAVING COUNT(*) >= 1000
ORDER BY fraud_rate_pct DESC;
```

Rates from small groups can change greatly with one additional fraud case. This filter is an exploratory choice, not a statistical significance test. We have only about two days of observations.

</details>

## 5. Evaluate a new alert threshold

Add 250 to `07_threshold_tradeoffs.sql`, rerun the analysis, and compare alert count, precision, and recall. What tradeoff would an analyst explain?

<details><summary>Solution</summary>

Add `(250)` to the `VALUES` list. Lower thresholds create a superset of the higher threshold's alerts, so alert count and recall cannot decrease. Precision may move either way. Report all three metrics and false positives; do not select a production rule using this in-sample exercise.

</details>

## 6. Explain duplicates

Why are duplicate rows retained? What evidence would justify removing them?

<details><summary>Solution</summary>

Identical visible fields may represent multiple underlying events. Without a reliable transaction identifier or source documentation proving duplicate ingestion, dropping them makes an unverified assumption. A sensitivity analysis can compare retained versus deduplicated results while clearly reporting the policy change. The main project retains all 284,807 rows.

</details>
