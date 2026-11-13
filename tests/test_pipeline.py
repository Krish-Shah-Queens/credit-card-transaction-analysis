"""Small, hand-authored fixtures exercise data rules; tests never download data."""
import csv
import json
import sys
from pathlib import Path

import duckdb
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_database import build_database
from common import COLUMNS
from download_data import download


def write_csv(path, records):
    with path.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(COLUMNS)
        for record in records:
            row = {column: 0 for column in COLUMNS}
            row.update(record)
            writer.writerow([row[column] for column in COLUMNS])
    return path


@pytest.fixture
def database(tmp_path):
    rows = [
        {"Time": 0, "Amount": 0, "Class": 0},
        {"Time": 3600, "Amount": 100, "Class": 1},
        {"Time": 3600, "Amount": 100, "Class": 1},
        {"Time": 10800, "Amount": 1000, "Class": 0},
    ]
    path = tmp_path / "test.duckdb"
    build_database(write_csv(tmp_path / "input.csv", rows), path)
    return path


def query(database, name):
    with duckdb.connect(str(database), read_only=True) as connection:
        return connection.execute((ROOT / "sql" / name).read_text()).fetchdf()


def test_totals_duplicate_and_zero_policy(database):
    overview = query(database, "01_overview.sql").iloc[0]
    assert (overview.transaction_count, overview.fraud_count, overview.total_amount) == (4, 2, 1200)
    assert overview.fraud_rate_pct == 50
    with duckdb.connect(str(database), read_only=True) as connection:
        quality = json.loads(connection.execute("SELECT report_json FROM data_quality").fetchone()[0])
        assert quality["exact_duplicate_extra_rows"] == 1
        assert quality["zero_amount_rows"] == 1
        assert connection.execute("SELECT COUNT(DISTINCT transaction_id) FROM transactions").fetchone()[0] == 4


def test_band_boundaries_and_conservation(database):
    bands = query(database, "04_amount_bands.sql")
    assert dict(zip(bands.amount_band, bands.transaction_count)) == {"0 to <10": 1, "100 to <500": 2, "500+": 1}
    assert bands.total_amount.sum() == 1200
    deciles = query(database, "05_amount_concentration.sql")
    assert deciles.share_of_total_amount_pct.sum() == pytest.approx(100, abs=0.001)
    assert query(database, "02_class_summary.sql").transaction_count.sum() == 4
    assert query(database, "03_elapsed_hours.sql").transaction_count.sum() == 4


def test_threshold_precision_recall(database):
    rows = query(database, "07_threshold_tradeoffs.sql").set_index("threshold_amount")
    assert rows.loc[100, "alert_count"] == 3
    assert rows.loc[100, "precision_pct"] == pytest.approx(66.6667)
    assert rows.loc[100, "recall_pct"] == 100
    assert rows.loc[500, "false_positives"] == 1
    assert rows.loc[500, "false_negatives"] == 2


def test_missing_hours_and_zero_denominator(database):
    hours = query(database, "06_hourly_change.sql").set_index("elapsed_hour")
    assert hours.loc[2, "transaction_count"] == 0
    assert hours.loc[2, "change_pct"] == -100
    assert __import__("pandas").isna(hours.loc[3, "change_pct"])


@pytest.mark.parametrize("record", [
    {"Amount": -1}, {"Time": -1}, {"Class": 0.5}, {"Class": 2},
    {"V28": ""}, {"V1": "nan"}, {"Amount": "inf"},
])
def test_invalid_data_does_not_replace_good_database(tmp_path, database, record):
    before = database.read_bytes()
    source = write_csv(tmp_path / "bad.csv", [record])
    with pytest.raises(ValueError, match="validation failed"):
        build_database(source, database)
    assert database.read_bytes() == before


def test_empty_file_and_header_validation(tmp_path):
    source = write_csv(tmp_path / "empty.csv", [])
    with pytest.raises(ValueError, match="validation failed"):
        build_database(source, tmp_path / "test.duckdb")
    source.write_text("wrong,header\n1,2\n")
    with pytest.raises(ValueError, match="header"):
        build_database(source, tmp_path / "test.duckdb")


def test_no_fraud_or_alerts_produces_null_metrics(tmp_path):
    source = write_csv(tmp_path / "small.csv", [{"Amount": 1, "Class": 0}])
    database = tmp_path / "small.duckdb"
    build_database(source, database)
    result = query(database, "07_threshold_tradeoffs.sql")
    assert result.precision_pct.isna().all()
    assert result.recall_pct.isna().all()


def test_downloader_preserves_unrecognized_existing_file(tmp_path):
    path = tmp_path / "keep.csv"
    path.write_text("my file")
    with pytest.raises(ValueError, match="not overwritten"):
        download(path)
    assert path.read_text() == "my file"
