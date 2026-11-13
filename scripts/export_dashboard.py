"""Export a lossless amount histogram for the interactive browser dashboard.

Every source row contributes to a (elapsed hour, fraud label, amount) group.
The dashboard computes exact counts, totals, means and weighted quantiles
from these groups without shipping anonymized transaction-level features.
"""
import argparse
import json
from pathlib import Path

import duckdb

from common import DATABASE, ROOT


def export_dashboard(database=DATABASE, output=ROOT / "dashboard/data/transactions.json"):
    output = Path(output)
    with duckdb.connect(str(database), read_only=True) as con:
        groups = con.execute("""
            SELECT elapsed_hour, is_fraud, (amount * 100)::BIGINT AS amount_cents,
                   COUNT(*) AS transaction_count
            FROM transactions
            GROUP BY elapsed_hour, is_fraud, amount
            ORDER BY elapsed_hour, is_fraud, amount
        """).fetchall()
        quality = json.loads(con.execute("SELECT report_json FROM data_quality").fetchone()[0])
        first, last, count, total = con.execute("""
            SELECT MIN(elapsed_seconds), MAX(elapsed_seconds), COUNT(*), SUM(amount)
            FROM transactions
        """).fetchone()
    payload = {
        "schema_version": 1,
        "columns": ["elapsed_hour", "is_fraud", "amount_cents", "transaction_count"],
        "source": {
            "name": "ULB / Worldline Credit Card Fraud Detection",
            "url": "https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud",
            "mirror": "https://storage.googleapis.com/download.tensorflow.org/data/creditcard.csv",
            "license": "ODbL 1.0 (database), DbCL 1.0 (contents)",
            "sha256": quality["source_sha256"],
            "period": "September 2013; approximately two days",
        },
        "metadata": {
            "transaction_count": count,
            "total_amount_cents": int(total * 100),
            "first_elapsed_second": first,
            "last_elapsed_second": last,
            "exact_duplicate_extra_rows": quality["exact_duplicate_extra_rows"],
            "zero_amount_rows": quality["zero_amount_rows"],
            "missing_or_nonfinite_rows": quality["missing_or_nonfinite_rows"],
            "duplicate_policy": quality["duplicate_policy"],
            "amount_unit": "Dataset amount units; currency is not recorded in the CSV.",
            "group_count": len(groups),
        },
        "groups": groups,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, separators=(",", ":")) + "\n", encoding="utf-8")
    temporary.replace(output)
    print(f"Exported {count:,} transactions in {len(groups):,} groups to {output}")
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DATABASE)
    parser.add_argument("--output", type=Path, default=ROOT / "dashboard/data/transactions.json")
    args = parser.parse_args()
    export_dashboard(args.database, args.output)
