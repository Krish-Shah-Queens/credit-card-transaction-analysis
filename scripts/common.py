"""Shared paths and source details; scripts work from any current directory."""
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/creditcard.csv"
DATABASE = ROOT / "data/processed/transactions.duckdb"
REPORTS = ROOT / "reports/generated"
SOURCE_URL = "https://storage.googleapis.com/download.tensorflow.org/data/creditcard.csv"
SOURCE_SHA256 = "76274b691b16a6c49d3f159c883398e03ccd6d1ee12d9d8ee38f4b4b98551a89"
COLUMNS = ["Time", *[f"V{i}" for i in range(1, 29)], "Amount", "Class"]


def sha256(path):
    """Hash in chunks rather than reading a 150 MB file into memory."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
