"""Validate the external CSV and create a local DuckDB database."""
import argparse
import csv
import json
from pathlib import Path

import duckdb

from common import COLUMNS, DATABASE, RAW, sha256


def build_database(csv_path=RAW, database_path=DATABASE):
    csv_path, database_path = Path(csv_path), Path(database_path)
    if not csv_path.is_file():
        raise FileNotFoundError("CSV missing. First run: python scripts/download_data.py")
    with csv_path.open(newline="", encoding="utf-8-sig") as stream:
        if next(csv.reader(stream), []) != COLUMNS:
            raise ValueError("Expected the original ULB CSV header: Time,V1,...,V28,Amount,Class")
    database_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = database_path.with_name(database_path.name + ".building")
    temporary.unlink(missing_ok=True)
    try:
        with duckdb.connect(str(temporary)) as connection:
            # DuckDB scans the file, so pandas never loads the full transaction table.
            connection.execute("SET memory_limit='1GB'")
            relation = connection.read_csv(
                str(csv_path), header=True, columns={column: "DOUBLE" for column in COLUMNS}
            )
            relation.create_view("csv_input")
            connection.execute("CREATE TEMP TABLE raw_transactions AS SELECT * FROM csv_input")
            invalid_numeric = " OR ".join(
                f'"{column}" IS NULL OR NOT isfinite("{column}")' for column in COLUMNS
            )
            quality = connection.execute(f"""
                SELECT COUNT(*) AS row_count,
                       COUNT(*) FILTER (WHERE {invalid_numeric}) AS missing_or_nonfinite_rows,
                       COUNT(*) FILTER (WHERE "Time" < 0 OR "Amount" < 0) AS negative_rows,
                       COUNT(*) FILTER (WHERE "Class" NOT IN (0, 1)) AS invalid_label_rows,
                       COUNT(*) FILTER (WHERE "Amount" = 0) AS zero_amount_rows
                FROM raw_transactions
            """).fetchdf().iloc[0].astype(int).to_dict()
            if quality["row_count"] == 0 or any(quality[key] for key in (
                "missing_or_nonfinite_rows", "negative_rows", "invalid_label_rows"
            )):
                raise ValueError(f"Data validation failed; no database replaced: {quality}")
            # Repeated values are flagged, not silently removed: there is no source transaction ID.
            duplicate_columns = ", ".join(f'"{column}"' for column in COLUMNS)
            quality["exact_duplicate_extra_rows"] = int(connection.execute(f"""
                SELECT COALESCE(SUM(n - 1), 0) FROM (
                    SELECT COUNT(*) AS n FROM raw_transactions
                    GROUP BY {duplicate_columns} HAVING COUNT(*) > 1
                )
            """).fetchone()[0])
            features = ", ".join(f'"V{i}"' for i in range(1, 29))
            connection.execute(f"""
                CREATE TABLE transactions AS
                SELECT ROW_NUMBER() OVER () AS transaction_id,
                       "Time" AS elapsed_seconds,
                       FLOOR("Time" / 3600)::INTEGER AS elapsed_hour,
                       "Amount"::DECIMAL(18, 2) AS amount,
                       "Class"::TINYINT AS is_fraud,
                       {features}
                FROM raw_transactions
            """)
            quality["source_sha256"] = sha256(csv_path)
            quality["duplicate_policy"] = "Retained; source has no transaction identifiers."
            connection.execute("CREATE TABLE data_quality (report_json VARCHAR)")
            connection.execute("INSERT INTO data_quality VALUES (?)", [json.dumps(quality)])
        # The previous good database survives validation failures.
        temporary.replace(database_path)
    finally:
        temporary.unlink(missing_ok=True)
        Path(str(temporary) + ".wal").unlink(missing_ok=True)
    print(json.dumps(quality, indent=2))
    return quality


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, default=RAW)
    parser.add_argument("--database", type=Path, default=DATABASE)
    args = parser.parse_args()
    try:
        build_database(args.csv, args.database)
    except (OSError, ValueError, duckdb.Error) as error:
        parser.exit(1, f"Build failed: {error}\n")
