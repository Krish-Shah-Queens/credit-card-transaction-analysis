# Ledger — interactive transaction explorer

**[Open the hosted platform](https://credit-card-transaction-explorer.delightfulcloak8.chatgpt.site)**. The hosted copy keeps its owner's Site access settings. Anyone can use the public source to run their own copy with the steps below.

A browser-based platform answering three questions with the complete external ULB/Worldline dataset:

1. How much transaction value is represented, and what is a typical transaction?
2. During which elapsed hours does activity increase, decrease, or peak?
3. How do fraud-labeled and non-fraud transactions differ?

## Run in Codespaces or locally

From the project root:

```bash
python -m http.server 8000 --directory dashboard
```

In Codespaces, open the **Ports** tab and choose **Open in Browser** for port 8000. On your computer, open http://localhost:8000 . The included aggregate dataset is ready to use; the dashboard needs no Python dependencies, database server, API keys, or build step. Stop the server with Ctrl+C.

## Use the platform

- Choose an elapsed-hour range, label, and inclusive amount range; click **Apply**.
- Switch between Overview, Transaction activity, Fraud comparison, and Data explorer.
- Change the activity measure among transaction count, total amount, and fraud rate. Hover or focus bars for details; activate a bar to filter to that hour.
- Read every hour's exact counts and changes in the activity table.
- Compare both labels using transaction count, totals, mean, median, 95th percentile, maximum, and zero-amount shares.
- Search, sort, and page through grouped amounts in the explorer.
- **Export data** downloads the current view with dataset attribution. Explorer export includes all matching groups, not just the visible page, and honors its search.
- Open **Data & methodology** for source information, definitions, quality counts, and the complete downloadable dashboard data.

The label filter affects Overview, Activity, and Explorer. Fraud comparison intentionally retains both labels within the chosen hour and amount range; this context is displayed on the page. The explorer groups transactions by elapsed hour, label, and exact amount, and shows each group's frequency. It does not invent individual transaction or customer identities.

Amounts remain in integer cents for aggregation. Medians and percentiles use the weighted amount distribution with linear interpolation, matching DuckDB's continuous quantiles. Undefined metrics display a dash. First and final source windows can be partial. The historical source is not a live processing feed.

## Rebuild from the external source

```bash
python scripts/download_data.py
python scripts/build_database.py
python scripts/export_dashboard.py
```

The committed aggregate JSON is about 1.8 MB. Its provenance and metadata let the browser reconcile source row counts and exact total amount before showing results.

## Tests

```bash
node --test dashboard/analytics.test.mjs
python -m pytest -q
```

Code: MIT. Dataset derivative: ODbL 1.0 / DbCL 1.0, separately documented in [data/README.md](data/README.md).
