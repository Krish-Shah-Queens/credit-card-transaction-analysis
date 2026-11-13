# External dataset and attribution

## Source

This project uses the **ULB/Worldline Credit Card Fraud Detection** dataset, describing European card transactions observed over roughly two days in September 2013. It contains 284,807 rows, 31 fields, and 492 labels indicating fraud. Worldline and ULB's Machine Learning Group collected and studied the data.

- Original listing: https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud
- Tutorial documenting the mirror: https://www.tensorflow.org/tutorials/structured_data/imbalanced_data
- Downloaded file: https://storage.googleapis.com/download.tensorflow.org/data/creditcard.csv
- Additional dataset record: https://www.openml.org/d/1597
- Source checked: November 13, 2026.
- CSV SHA-256: `76274b691b16a6c49d3f159c883398e03ccd6d1ee12d9d8ee38f4b4b98551a89`

The downloader uses a fixed mirror URL and checks its bytes against the pinned hash. The builder stores the actual input hash in the database and the analysis exports it with the findings. A changed hash requires review, not silently accepting new content. A manually obtained Kaggle CSV may differ in byte formatting; the builder accepts the original schema and records its actual hash.

## Dataset terms versus code license

The original Kaggle listing labels its license **“Database: Open Database, Contents: Database Contents”**, referring to the Open Data Commons [Open Database License (ODbL) v1.0](https://opendatacommons.org/licenses/odbl/1-0/) and [Database Contents License (DbCL) v1.0](https://opendatacommons.org/licenses/dbcl/1-0/). This label was verified through Kaggle's dataset metadata endpoint on the date above. Review those source terms when reusing or redistributing data, including their attribution and applicable database-sharing obligations.

The repository's **MIT LICENSE applies to its code and original documentation**. It does not grant rights to, or replace the terms of, the external dataset. Raw CSVs and derived row-level databases are excluded from the archive and from Git. The included reports contain aggregate results, carry source attribution, and link to these terms. A download mirror is a distribution route, not a new data license.

Suggested dataset citation:

Andrea Dal Pozzolo, Olivier Caelen, Reid A. Johnson, and Gianluca Bontempi. *Calibrating Probability with Undersampling for Unbalanced Classification*. IEEE Symposium on Computational Intelligence and Data Mining (CIDM), 2015.

## Manual download

1. Open the original Kaggle listing above and download its dataset. A Kaggle account may be required.
2. Unzip it and place the original `creditcard.csv` in `data/raw/`.
3. Run `python scripts/build_database.py`, then `python scripts/analyze.py`.

Do not run the downloader over a manually supplied file with different bytes: it deliberately refuses to overwrite unrecognized files. The build command accepts an alternative input via `--csv path/to/creditcard.csv` and output database via `--database path/to/transactions.duckdb`. The analysis accepts the matching `--database` and an `--output` folder. Inputs must have the original schema.

## Scope and limitations

`V1`–`V28` are anonymized PCA components. They have no exposed merchant or demographic meaning. `Time` is elapsed seconds relative to the first observation, not a date or local time. The project labels amounts as “dataset amount units” because the file does not contain a currency field.

All observations are preserved after validation, including zero amounts and exactly repeated field values. There is no original unique transaction key with which to confirm duplicate events. An added local row number identifies stored rows only. The project reports duplicates so a learner can explore the effect of a different documented policy separately.

Fraud labels are a small fraction of the sample. An always-non-fraud classifier would have high accuracy but zero fraud recall. Amount-only alert rules here are descriptive demonstrations evaluated on the same source data, with no training, held-out evaluation, calibration, or operational recommendation. Any future predictive extension needs temporal validation, leakage controls, and precision/recall-oriented evaluation.
