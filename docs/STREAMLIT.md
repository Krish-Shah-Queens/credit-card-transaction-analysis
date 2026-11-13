# Run the Python dashboard

The primary dashboard uses **Streamlit + Plotly + DuckDB**, matching the stack used in comparable Python/SQL analytics projects. It includes interactive analysis, original-label comparisons, model evaluation, and CSV scoring. The bundled aggregate data, saved detector, and evaluation report make it usable immediately without downloading or training anything.

## Your existing Codespace

In the terminal at the bottom, run these two commands. Copy the command lines, without Markdown backticks:

```bash
git pull
bash scripts/run_dashboard.sh
```

The launcher installs the project dependencies and starts Streamlit. In **Ports**, locate **8501** and select **Open in Browser**. Leave that terminal running while using the app. Stop with Ctrl+C.

If Git reports local changes, preserve those changes before pulling. The launcher does not reset or overwrite your work. A newly created Codespace already uses the latest source; just run the second command.

## Local Python environment

Create and activate the virtual environment described in the root README, then:

```bash
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

Open the URL printed by Streamlit, usually http://localhost:8501 .

## Publish on Streamlit Community Cloud

The complete app is prepared in GitHub. It has not been deployed to a Streamlit Cloud account from this session. The live `chatgpt.site` URL is the separate browser preview.

1. Sign in at https://share.streamlit.io and authorize your GitHub account.
2. Choose **Create app**, then select:

| Field | Value |
| --- | --- |
| Repository | `Krish-Shah-Queens/credit-card-transaction-analysis` |
| Branch | `main` |
| Main file | `streamlit_app.py` |
| Python version | `3.12` |

3. Click **Deploy**. The service installs the committed `requirements.txt` and provides a `streamlit.app` URL. No API keys or secrets are needed for this application.

## Pages

- **Payments overview:** weighted totals, count, median, and source fraud-label rate.
- **Transaction activity:** interactive Plotly time series, selectable measure, exact hourly changes, and CSV export.
- **Source fraud labels:** original Class provenance, amount profiles, and distributions normalized within each label.
- **Model evaluation:** held-out precision/recall, confusion matrix, adjustable score threshold, validation comparison, and examples.
- **Score transactions:** upload up to 10,000 rows of compatible ULB PCA features and Amount; keep supplied labels separate from model decisions.
- **Data explorer:** searchable, sortable weighted amount groups and export.
- **Data & method:** dataset provenance, framework, hosting, and interpretation limits.

The source analysis filters apply to analysis pages. Model evaluation always uses its complete chronological holdout; upload scoring uses only the supplied upload. A model flag never overwrites a source label. See [MODEL_CARD.md](MODEL_CARD.md) for training details and limits.
