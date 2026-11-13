# Dashboard data — ODbL / DbCL

`transactions.json` is an aggregate derivative of the **Worldline / ULB Machine Learning Group Credit Card Fraud Detection dataset**, originally published at https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud and downloaded from the public mirror documented by TensorFlow at https://www.tensorflow.org/tutorials/structured_data/imbalanced_data.

The database is made available under the **Open Data Commons Open Database License (ODbL) v1.0**: https://opendatacommons.org/licenses/odbl/1-0/ . Individual database contents are covered by the **Database Contents License (DbCL) v1.0**: https://opendatacommons.org/licenses/dbcl/1-0/ . The project's MIT license does not apply to this data file. Preserve dataset attribution and these terms when sharing the data or a derivative database.

Each group is `[elapsed_hour, is_fraud, amount_cents, transaction_count]`. Group frequencies retain all 284,807 source observations, including repeated source rows and zero-amount transactions. Amounts are expressed in dataset units; the CSV does not declare currency. This aggregation removes the anonymized PCA features and sub-hour timing while preserving exact amount distributions within each elapsed hour and label.

The full dashboard data is available from the site's Data & methodology dialog and this repository. Reproduce it with `python scripts/export_dashboard.py` after building the local DuckDB database. The source URL, source SHA-256, row count, and total amount are embedded in the JSON.

Dataset citation: Andrea Dal Pozzolo, Olivier Caelen, Reid A. Johnson, and Gianluca Bontempi. *Calibrating Probability with Undersampling for Unbalanced Classification*. IEEE CIDM, 2015.
