"""Download the external ULB dataset from TensorFlow's public CSV mirror."""
import argparse
from pathlib import Path
import urllib.request

from common import RAW, SOURCE_SHA256, SOURCE_URL, sha256


def download(destination=RAW):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if sha256(destination) == SOURCE_SHA256:
            print(f"Verified existing dataset: {destination}")
            return destination
        raise ValueError(
            "Existing file differs from the pinned mirror. It was not overwritten. "
            "Use --output with a new path, or build directly from a manually downloaded CSV."
        )
    temporary = destination.with_suffix(destination.suffix + ".part")
    try:
        # TLS verification uses Python's default certificate verification.
        with urllib.request.urlopen(SOURCE_URL, timeout=60) as response:
            with temporary.open("wb") as output:
                while block := response.read(1024 * 1024):
                    output.write(block)
        if sha256(temporary) != SOURCE_SHA256:
            raise ValueError("Dataset checksum changed. Review the source before using this file.")
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Downloaded and verified {destination.stat().st_size:,} bytes: {destination}")
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=RAW)
    args = parser.parse_args()
    try:
        download(args.output)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Download failed: {error}\nSee docs/DATASET.md for manual download instructions.\n")
