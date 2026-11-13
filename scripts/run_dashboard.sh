#!/usr/bin/env bash
# Run from GitHub Codespaces, or from an activated local Python environment.
set -eu
cd "$(dirname "$0")/.."
python -m pip install -r requirements.txt
exec python -m streamlit run streamlit_app.py --server.address 0.0.0.0 --server.port 8501
