# Data dictionary and validation

## Source CSV

| Field | Meaning | Ingest type |
| --- | --- | --- |
| `Time` | Seconds since the first observed transaction | DOUBLE |
| `V1`–`V28` | Anonymized numerical PCA components | DOUBLE |
| `Amount` | Transaction amount; no currency column is provided | DOUBLE, then DECIMAL(18,2) |
| `Class` | 1 = fraud label, 0 = non-fraud label | DOUBLE for validation, then TINYINT |

The CSV is read with explicit numeric types. A nonnumeric token or malformed row fails ingestion. The full header must match the original field names and order. Empty data, missing values, non-finite numeric values, negative time/amount values, and labels outside `{0, 1}` fail validation. Checking labels before converting to an integer prevents fractional values being silently rounded. Valid source amounts are stored to two decimal places; this schema is intended for the original ULB CSV.

## Local `transactions` table

| Field | Meaning | Type |
| --- | --- | --- |
| `transaction_id` | Locally assigned row number; not a source identity or customer ID | BIGINT |
| `elapsed_seconds` | Original `Time` | DOUBLE |
| `elapsed_hour` | `FLOOR(elapsed_seconds / 3600)` | INTEGER |
| `amount` | Original amount in fixed-point storage | DECIMAL(18,2) |
| `is_fraud` | Original binary `Class` | TINYINT |
| `V1`–`V28` | Original anonymized components | DOUBLE |

`data_quality` holds one JSON string containing row counts, input SHA-256, validation counts, and the duplicate policy. SQL queries run against `transactions`. The source file is unchanged.

## Metrics

| Metric | Definition |
| --- | --- |
| Fraud rate (%) | 100 × fraud-labeled rows / all rows |
| Total amount | Sum of transaction amounts; not revenue or loss |
| Median amount | Middle amount after sorting; less affected by large values than the mean |
| Exact duplicate extra rows | Sum of `group_size - 1` across identical full source rows |
| Precision (%) | 100 × labeled fraud among alerts / all alerts |
| Recall (%) | 100 × labeled fraud among alerts / all labeled fraud |
| Alert rate (%) | 100 × alerts / all rows |

An undefined denominator produces SQL `NULL`, not a misleading zero. Hourly percentage changes also return `NULL` when there is no previous hour or its count is zero. Missing elapsed hours are filled with zero counts in the change query. First and last hourly windows may not represent a full hour. Amount deciles split **transactions**, not people, into nearly equal-sized groups.
