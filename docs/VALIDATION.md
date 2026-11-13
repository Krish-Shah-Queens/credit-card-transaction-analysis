# Validation record

Verified on November 13, 2026, with Python 3.12.14, DuckDB 1.4.2, pandas 2.3.3, and Matplotlib 3.10.7 on Linux.

## Complete external dataset

The downloader verifies the CSV's pinned SHA-256. The build and all seven SQL queries ran on the complete external source. The notebook was executed from its first cell to its last; its saved outputs are included. Fresh report output was copied to `reports/example` after validation.

| Check | Observed result |
| --- | ---: |
| Source rows / stored rows | 284,807 / 284,807 |
| Fraud labels | 492 |
| Non-fraud labels | 284,315 |
| Fraud rate | 0.172749% (rounded to six decimals) |
| Total transaction amount | 25,162,590.01 |
| Median transaction amount | 22.00 |
| Exact duplicate extra rows | 1,081, retained |
| Zero-amount rows | 1,825, retained |
| Missing or non-finite rows | 0 |
| Negative amount/time rows | 0 |
| Invalid-label rows | 0 |

Counts, fraud-label totals, amount totals, and zero-amount counts were also independently reconciled with a chunked pandas scan of the original CSV. Amount-band and class subtotals sum to the full population; amount-decile shares sum to 100% within rounding. The simple threshold results are descriptive in-sample calculations.

## Automated tests

`python -m pytest -q` passes 14 tests, including parametrized invalid-data cases. Tests run offline on small hand-authored fixtures, covering:

- Duplicate retention, zero-amount retention, and distinct local row keys.
- Totals, label rates, amount-band boundaries, and concentration shares.
- Explicit precision, recall, false-positive, and false-negative expectations.
- Empty elapsed-hour filling and undefined percentage changes.
- Rejection of negative values, fractional/invalid labels, missing values, NaN, infinity, empty input, and wrong headers.
- Preservation of the existing database after a failed validation.
- Preservation of an existing unrecognized file by the downloader.

The GitHub Actions workflow is configured for Python 3.11 and 3.12. Only Python 3.12 was executed locally here; hosted CI will run after publication. Windows and macOS were not tested in this environment.

## Reproduce

```bash
python scripts/download_data.py
python scripts/build_database.py
python scripts/analyze.py
python -m pytest -q
python -m nbconvert --to notebook --execute --inplace notebooks/01_credit_card_analysis.ipynb
```

For the notebook and tests, first install `requirements-dev.txt`. No dataset access is needed for unit tests; network access is needed for an uncached download.
