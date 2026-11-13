# Dashboard research and implementation choice

Reviewed November 13, 2026. This is a selection of comparable public projects and official documentation, not a survey measuring market share. The implementation is original; these sources informed its framework and interaction patterns.

## What comparable projects use

| Tool | Typical role | Fit here |
| --- | --- | --- |
| Streamlit + Plotly | Python data apps with filters, interactive charts, tables, and model demos | Selected primary implementation: `streamlit_app.py` |
| Plotly Dash | Python analytical applications with explicit callbacks and interactive chart events | A viable alternative when more application control is needed |
| Power BI / Tableau | Dedicated business-intelligence report authoring and publishing | Useful for business reporting; the current project benefits from keeping model training and application logic in open Python source |
| Sites | Hosting the existing HTML/JavaScript browser preview | A hosting service for the separate preview, not the Streamlit Python application framework |

## Comparable projects reviewed

- [indfir/credit-card-fraud-detection](https://github.com/indfir/credit-card-fraud-detection): describes a Streamlit BI dashboard with fraud analysis, a confusion matrix, and a threshold simulator. Adopted pattern: keep observed labels, predicted alerts, and operating-point evaluation separate.
- [Kbod999/fintech-fraud-analytics](https://github.com/Kbod999/fintech-fraud-analytics): combines Python, SQL, Plotly, and Streamlit on the ULB dataset. Adopted pattern: keep SQL and analysis as reusable project code, with a Python dashboard as the interface.
- [Plotly Dash overview](https://plotly.com/dash/): documents a Python alternative for analytical applications and linked chart interactions.

These references establish that Streamlit/Plotly is used in comparable projects; they do not establish that any example's modeling methodology is correct. Our data split, preprocessing, and evaluation were implemented and tested independently.

## Interaction patterns reviewed

- [Stripe Radar analytics](https://docs.stripe.com/radar/analytics): a dedicated analytical workspace. Applied as separate source-label and model-evaluation views; this dataset does not support Stripe-style disputes or payment outcomes.
- [Adyen risk performance](https://docs.adyen.com/risk-management/dispute-and-fraud-monitoring/): shared filter scope and progressively detailed risk views. Applied as clearly scoped time/amount analysis and a fixed holdout evaluation scope.
- [Metabase dashboard practices](https://www.metabase.com/learn/metabase-basics/querying-and-dashboards/dashboards/bi-dashboard-best-practices): clear hierarchy and interactive exploration. Applied as sidebar filters, top-level KPIs, a main time-series view, and exact detail tables.

We did not add unsupported merchant, geography, currency, chargeback, or real-time metrics. The two-day source remains visibly historical.

## Framework versus hosting

Streamlit runs a Python server. It can run in Codespaces, on a local machine, or on Streamlit Community Cloud. Plotly renders interactive charts inside it, and DuckDB aggregates data with SQL.

The existing Site URL remains a separate static preview using JavaScript and the same saved aggregate data and model evaluation. It cannot run the Streamlit Python server or score uploaded features with the Python model. The Streamlit app provides that additional scoring page.

Official deployment instructions: [Streamlit Community Cloud deployment](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy). Community Cloud publication requires its own signed-in account and GitHub authorization; connecting GitHub in this chat does not create that session.
