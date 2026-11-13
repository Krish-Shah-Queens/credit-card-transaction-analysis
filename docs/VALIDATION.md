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

`python -m pytest -q` passes 15 tests, including parametrized invalid-data cases. Tests run offline on small hand-authored fixtures, covering:

- Duplicate retention, zero-amount retention, and distinct local row keys.
- Totals, label rates, amount-band boundaries, and concentration shares.
- Explicit precision, recall, false-positive, and false-negative expectations.
- Empty elapsed-hour filling and undefined percentage changes.
- Rejection of negative values, fractional/invalid labels, missing values, NaN, infinity, empty input, and wrong headers.
- Preservation of the existing database after a failed validation.
- Preservation of an existing unrecognized file by the downloader.
- Dashboard export conservation of source frequencies and integer-cent amount totals.

The GitHub Actions workflow is configured for Python 3.11 and 3.12. Only Python 3.12 was executed locally here; hosted CI will run after publication. Windows and macOS were not tested in this environment.

## Interactive platform verification

The dashboard represents all 284,807 source observations in 126,501 `(elapsed hour, label, exact amount)` groups, preserving their transaction frequencies. Browser-side calculations were independently reconciled against DuckDB over **360 metric checks in 12 filter scenarios**, including label-only selections, single hours, amount boundaries, zero-amount transactions, and empty selections. Continuous quantiles were compared against SQL DOUBLE calculations to avoid fixed-point output truncation below one cent.

`node --test dashboard/analytics.test.mjs` passes seven tests for frequency-weighted statistics, inclusive filter boundaries, comparison scope, empty hours, amount bands, empty selections, and CSV escaping. Node-based DOM interaction checks also passed for dataset loading, navigation, filters, comparison scope, search, validation, reset, and the data dialog. These interaction checks used a DOM implementation, not a visual browser.

Visual browser QA was unavailable in the managed session because its browser-control tool was not exposed. No preview server or alternative browser-control route was started. The static assets, JavaScript syntax, calculations, DOM interactions, source reconciliation, and hosted deployment were checked; responsive layout still needs a visual browser check.

## Streamlit application and predictive extension

The Python suite now passes **28 tests**, including training/validation/test separation, target and time exclusion from features, invalid-input rejection, inclusive score thresholds, saved-artifact hash checks, and frequency-weighted summaries. Streamlit's AppTest ran all seven pages, changed the model threshold, checked that source analysis counts and filters survived navigation, and exercised an empty filter selection without a server or browser.

The browser-preview suite passes **eight tests**, including confusion-count and precision/recall calculations. DOM checks additionally exercised the model slider, validation-threshold reset, and the model page's fixed filter scope. A visual browser test remains unverified; AppTest and DOM tests do not validate browser layout.

The training pipeline was executed on the external source: two candidate models were fit only on the chronological training split, selected by validation average precision, and evaluated on the later holdout. At the validation-selected threshold, the held-out confusion counts are 54 true positives, 10 false positives, 20 false negatives, and 56,662 true negatives. The full protocol, limitations, and source/model label distinction are recorded in [MODEL_CARD.md](MODEL_CARD.md).

## Reproduce

```bash
python scripts/download_data.py
python scripts/build_database.py
python scripts/analyze.py
python -m pytest -q
python -m nbconvert --to notebook --execute --inplace notebooks/01_credit_card_analysis.ipynb
```

For the notebook and tests, first install `requirements-dev.txt`. No dataset access is needed for unit tests; network access is needed for an uncached download.
