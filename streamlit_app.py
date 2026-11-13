"""Ledger: a Python/SQL dashboard inspired by common Streamlit analytics projects."""
import hashlib
import json
from pathlib import Path

import duckdb
import joblib
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from platform_logic import operating_metrics, summary
from scripts.train_fraud_model import FEATURES, make_features

ROOT = Path(__file__).resolve().parent
TEAL, AMBER = "#078477", "#c37724"
st.set_page_config(page_title="Ledger | Transaction Analytics", page_icon="💳", layout="wide")


@st.cache_data
def load_data():
    payload = json.loads((ROOT / "dashboard/data/transactions.json").read_text())
    groups = pd.DataFrame(payload["groups"], columns=payload["columns"])
    assert int(groups.transaction_count.sum()) == payload["metadata"]["transaction_count"]
    assert int((groups.amount_cents * groups.transaction_count).sum()) == payload["metadata"]["total_amount_cents"]
    return payload, groups


@st.cache_data
def load_report():
    return json.loads((ROOT / "dashboard/data/model_evaluation.json").read_text())


@st.cache_resource
def load_detector(expected_sha):
    path = ROOT / "models/fraud_detector.joblib"
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
        raise ValueError("Model artifact does not match the committed evaluation report.")
    return joblib.load(path)


def amount(cents):
    return "—" if cents is None else f"{cents / 100:,.2f}"


def rate(value):
    return "—" if value is None else f"{100 * value:.2f}%"


def style_chart(figure, title=None):
    figure.update_layout(template="plotly_white", title=title, margin=dict(l=10, r=10, t=35, b=10),
                         paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                         font=dict(family="sans-serif", color="#38534e"),
                         legend=dict(orientation="h", y=1.1), height=330)
    return figure


def chart(figure, key):
    st.plotly_chart(style_chart(figure), width="stretch", key=key, config={"displaylogo": False})


def hourly(groups, first, last):
    # SQL aggregates weighted groups; interpolation and blank-hour handling stay explicit.
    with duckdb.connect() as con:
        con.register("selected", groups)
        result = con.execute("""
            SELECT elapsed_hour, SUM(transaction_count)::BIGINT AS transactions,
                   SUM(amount_cents * transaction_count) / 100.0 AS total_amount,
                   SUM(is_fraud * transaction_count)::BIGINT AS source_fraud
            FROM selected GROUP BY elapsed_hour ORDER BY elapsed_hour
        """).fetchdf()
    result = result.set_index("elapsed_hour").reindex(range(first, last + 1), fill_value=0).reset_index()
    previous = result.transactions.shift()
    result["count_change_pct"] = 100 * (result.transactions - previous) / previous.replace(0, float("nan"))
    result["source_fraud_rate_pct"] = 100 * result.source_fraud / result.transactions.replace(0, float("nan"))
    return result


def show_label_provenance():
    st.info("Source labels: original Class = 1 → fraud; Class = 0 → non-fraud. "
            "The application preserves these labels. Model flags are separate predictions.")


payload, groups = load_data()
with st.sidebar:
    st.title("ledger.")
    st.caption("TRANSACTION INTELLIGENCE")
    page = st.radio("Workspace", ["Payments overview", "Transaction activity", "Source fraud labels",
                                 "Model evaluation", "Score transactions", "Data explorer", "Data & method"], key="page")
    first, last = 0, 47
    base = selected = groups
    if page in {"Payments overview", "Transaction activity", "Source fraud labels", "Data explorer"}:
        saved = st.session_state.get("analysis_filters", {"hours": (0, 47), "label": "All labels", "minimum": 0., "maximum": 25691.16})
        for key, value in saved.items():
            if key not in st.session_state:
                st.session_state[key] = value
        st.divider()
        first, last = st.slider("Elapsed hours", 0, 47, key="hours")
        label = st.selectbox("Source label", ["All labels", "Class 0 · non-fraud", "Class 1 · fraud"], key="label")
        low, high = st.columns(2)
        minimum = low.number_input("Min amount", min_value=0., step=1., key="minimum")
        maximum = high.number_input("Max amount", min_value=0., step=1., key="maximum")
        st.session_state["analysis_filters"] = {"hours": (first, last), "label": label, "minimum": minimum, "maximum": maximum}
        if minimum > maximum:
            st.error("Minimum amount must be at most the maximum.")
            st.stop()
        base = groups[(groups.elapsed_hour.between(first, last)) &
                      (groups.amount_cents.between(round(minimum * 100), round(maximum * 100)))]
        selected = base if label == "All labels" else base[base.is_fraud == int(label[6])]
        st.caption("Times are elapsed hours, not clock times. Amounts use dataset units.")
    else:
        st.caption("Model pages use their explicitly stated holdout or upload, independently of analysis filters.")
    st.divider()
    st.caption("ULB / Worldline · September 2013")
    st.write("284,807 source transactions")
    st.link_button("Open-source repository ↗", "https://github.com/Krish-Shah-Queens/credit-card-transaction-analysis")

st.caption("LEDGER / CREDIT CARD ANALYTICS")
st.title(page)

if page in {"Payments overview", "Transaction activity", "Data explorer"}:
    s = summary(selected)
    st.caption(f"{s['count']:,} matching transactions · elapsed hours {first}–{last} · historical external data")
    a, b, c, d = st.columns(4)
    a.metric("Total transaction value", amount(s["total"]), border=True)
    b.metric("Transactions", f"{s['count']:,}", border=True)
    c.metric("Typical amount · median", amount(s["median"]), border=True)
    d.metric("Source-labeled fraud", rate(s["fraud_rate"]), border=True)
    if not s["count"]:
        st.warning("No matching observations. Widen the filters in the sidebar.")
    hours = hourly(selected, first, last)
    if page in {"Payments overview", "Transaction activity"}:
        measure = st.radio("Activity measure", ["Transactions", "Transaction value", "Source fraud rate"],
                           horizontal=True, key="measure")
        field = {"Transactions": "transactions", "Transaction value": "total_amount", "Source fraud rate": "source_fraud_rate_pct"}[measure or "Transactions"]
        figure = px.line(hours, x="elapsed_hour", y=field, markers=True,
                         labels={"elapsed_hour": "Elapsed hour since first transaction", field: measure},
                         color_discrete_sequence=[TEAL])
        if field != "source_fraud_rate_pct":
            figure.update_traces(fill="tozeroy", fillcolor="rgba(7,132,119,.08)")
        chart(figure, "activity_chart")
        st.caption("Hover, zoom, or select a range. Source hour 47 is partial; these are not local clock hours.")
    if page == "Payments overview":
        left, right = st.columns([1.2, 1])
        with left:
            st.subheader("Transaction profile")
            st.write(f"The median transaction is **{amount(s['median'])}**; the mean is **{amount(s['mean'])}**.")
            profile = pd.DataFrame({"Measure": ["Mean", "Median", "95th percentile", "Maximum"],
                                    "Amount": [s["mean"], s["median"], s["p95"], s["maximum"]]})
            profile["Amount"] = profile.Amount.map(amount)
            st.dataframe(profile, hide_index=True, width="stretch")
        with right:
            st.subheader("Labels at a glance")
            show_label_provenance()
            st.write(f"**{s['fraud']:,}** source fraud labels among **{s['count']:,}** selected observations.")
            st.caption("The source does not describe each case's investigation. A high amount alone does not assign a fraud label.")
    elif page == "Transaction activity":
        st.subheader("Exact hourly detail")
        st.dataframe(hours, hide_index=True, width="stretch")
        st.download_button("Download hourly data", hours.to_csv(index=False), "ulb-hourly.csv", "text/csv")
    else:
        st.info("Each row groups the same exact amount, elapsed hour, and source label. Frequencies represent all observations; these are not unique transaction IDs.")
        display = selected.copy()
        search = st.text_input("Search an exact amount (optional)", key="explorer_search")
        if search:
            try:
                display = display[display.amount_cents == round(float(search) * 100)]
            except ValueError:
                st.warning("Enter a numeric amount, for example 22.00.")
                display = display.iloc[:0]
        display["amount"] = display.amount_cents / 100
        display = display.drop(columns="amount_cents").sort_values("amount", ascending=False)
        st.dataframe(display, hide_index=True, width="stretch")
        st.download_button("Download matching amount groups", display.to_csv(index=False), "ulb-amount-groups.csv", "text/csv")

elif page == "Source fraud labels":
    show_label_provenance()
    st.caption("Comparing both source labels within the time and amount filters. The label selector is deliberately ignored for this comparison.")
    comparisons = [summary(base[base.is_fraud == label]) for label in [0, 1]]
    a, b = st.columns(2)
    for column, label, s in zip([a, b], ["Class 0 · non-fraud", "Class 1 · fraud"], comparisons):
        with column:
            st.metric(label, f"{s['count']:,}", border=True)
            st.caption(f"Median {amount(s['median'])} · mean {amount(s['mean'])}")
    metrics = ["count", "total", "mean", "median", "p95", "maximum", "zero"]
    comparison = pd.DataFrame({"Measure": ["Transactions", "Total value", "Mean", "Median", "95th percentile", "Maximum", "Zero amounts"],
                               "Class 0 · non-fraud": [f"{comparisons[0][m]:,}" if m in {"count", "zero"} else amount(comparisons[0][m]) for m in metrics],
                               "Class 1 · fraud": [f"{comparisons[1][m]:,}" if m in {"count", "zero"} else amount(comparisons[1][m]) for m in metrics]})
    st.dataframe(comparison, hide_index=True, width="stretch")
    bands = base.copy()
    bands["Amount band"] = pd.cut(bands.amount_cents, [-1, 999, 4999, 9999, 49999, float("inf")],
                                  labels=["0–<10", "10–<50", "50–<100", "100–<500", "500+"])
    distribution = bands.groupby(["is_fraud", "Amount band"], observed=False).transaction_count.sum().reset_index()
    totals = distribution.groupby("is_fraud").transaction_count.transform("sum")
    distribution["Share within label (%)"] = 100 * distribution.transaction_count / totals.replace(0, float("nan"))
    distribution["Source label"] = distribution.is_fraud.map({0: "Class 0 · non-fraud", 1: "Class 1 · fraud"})
    chart(px.bar(distribution, x="Amount band", y="Share within label (%)", color="Source label", barmode="group",
                 color_discrete_sequence=[TEAL, AMBER], hover_data=["transaction_count"]), "label_distribution")
    st.caption("Percentages within each label make the differently sized groups comparable. They describe associations, not causes.")

elif page == "Model evaluation":
    report = load_report()
    st.info(f"{report['model_name']} · predictions on a later, held-out period. Source Class labels remain unchanged.")
    st.caption("This page uses the complete chronological test split; it is independent of the analysis sidebar filters.")
    threshold = st.slider("Model flag threshold · score is not a calibrated probability", 0., 1.,
                          float(report["recommended_threshold"]), .001, format="%.3f", key="threshold")
    m = operating_metrics(report["test_curve"][round(threshold * 1000)])
    a, b, c, d = st.columns(4)
    a.metric("Predicted alerts", f"{m['alerts']:,}", border=True)
    b.metric("Precision · fraud among alerts", rate(m["precision"]), border=True)
    c.metric("Recall · fraud labels caught", rate(m["recall"]), border=True)
    d.metric("Fraud labels missed", f"{m['fn']:,}", border=True)
    st.caption(f"Validation-selected threshold: {report['recommended_threshold']:.3f}. "
               f"Test average precision: {report['test_average_precision']:.4f}; test fraud prevalence: {rate(report['test_prevalence'])}. "
               "Changing this slider explores the test data; it is not a new unbiased evaluation.")
    left, right = st.columns(2)
    with left:
        st.subheader("Predictions versus source labels")
        figure = go.Figure(go.Heatmap(z=[[m["tn"], m["fp"]], [m["fn"], m["tp"]]],
                                     x=["Not flagged", "Flagged"], y=["Source Class 0", "Source Class 1"],
                                     text=[[f"True negatives: {m['tn']:,}", f"False positives: {m['fp']:,}"],
                                           [f"False negatives: {m['fn']:,}", f"True positives: {m['tp']:,}"]],
                                     texttemplate="%{text}", colorscale="Teal", showscale=False))
        chart(figure, "confusion_matrix")
    with right:
        st.subheader("Precision–recall tradeoff")
        curve = pd.DataFrame([operating_metrics(row) for row in report["test_curve"]])
        figure = px.line(curve, x="recall", y="precision", hover_data=["threshold", "alerts"], color_discrete_sequence=[TEAL])
        figure.add_hline(y=report["test_prevalence"], line_dash="dot", annotation_text="Test prevalence baseline")
        chart(figure, "pr_curve")
    with st.expander("How the model was trained and selected", expanded=True):
        st.write(report["split_method"])
        st.dataframe(pd.DataFrame(report["splits"]).T, width="stretch")
        st.write(report["selection"])
        st.dataframe(pd.DataFrame(report["validation_candidates"]), hide_index=True, width="stretch")
        st.caption(report["threshold_selection"])
    st.subheader("Review held-out examples")
    examples = pd.DataFrame(report["examples"])
    examples["model_flag"] = examples.model_score.ge(threshold)
    st.dataframe(examples, hide_index=True, width="stretch")
    st.caption(report["example_selection"])
    with st.expander("Model limits"):
        for limitation in report["limitations"]:
            st.write("• " + limitation)

elif page == "Score transactions":
    report = load_report()
    st.info("Upload numerical ULB-format features to obtain model flags. A flag suggests review; it does not confirm fraud or change a source label.")
    st.caption("Required columns: V1–V28 and Amount. Time and Class are excluded from prediction. Scores are not calibrated probabilities.")
    st.caption("V1–V28 must use the same ULB PCA representation as the training source. An arbitrary bank transaction cannot be scored from amount and time alone; the original PCA transformation is unavailable.")
    threshold = st.slider("Flag threshold", 0., 1., float(report["recommended_threshold"]), .001, key="score_threshold")
    st.download_button("Download CSV header template", ",".join(FEATURES) + "\n", "feature-template.csv", "text/csv")
    uploaded = st.file_uploader("ULB-format CSV · up to 10,000 rows", type="csv")
    if uploaded:
        try:
            incoming = pd.read_csv(uploaded, nrows=10001)
            if incoming.empty or len(incoming) > 10000:
                raise ValueError("Supply between 1 and 10,000 transactions.")
            features = make_features(incoming)
            scores = load_detector(report["artifact_sha256"]).predict_proba(features)[:, 1]
            scored = pd.DataFrame({"upload_row": range(1, len(incoming) + 1), "amount": incoming.Amount,
                                   "model_score": scores, "model_flag": scores >= threshold})
            if "Class" in incoming:
                scored["provided_Class_not_used_for_prediction"] = incoming.Class
            st.metric("Transactions flagged for review", int(scored.model_flag.sum()))
            st.dataframe(scored, hide_index=True, width="stretch")
            st.download_button("Download model results", scored.to_csv(index=False), "model-results.csv", "text/csv")
        except (ValueError, OSError) as error:
            st.error(str(error))

else:
    show_label_provenance()
    st.markdown("""### What the source provides
    Worldline and ULB's Machine Learning Group published an anonymized credit card dataset from approximately two days in September 2013. The original `Class` field contains the historical labels. The case-by-case adjudication process is not provided.

    ### What this project adds
    DuckDB SQL summaries, Streamlit filters, Plotly interactive charts, and separately evaluated model flags. The predictive model uses V1–V28 and log-transformed Amount; it never uses Class as an input. Original PCA feature meanings cannot be recovered.

    ### Framework and hosting
    Streamlit is the Python application framework, Plotly supplies interactive charts, and DuckDB runs SQL. This app can run locally, in Codespaces, or on Streamlit Community Cloud. Sites hosts the separate browser preview; it is not the Streamlit Python runtime.

    ### Source terms
    [ULB / Worldline dataset](https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud): ODbL 1.0 / DbCL 1.0. Code and original documentation: MIT. The aggregate data and selected held-out examples retain source attribution. Amounts are dataset units; no currency field is provided.
    """)
    st.json(payload["metadata"])

st.divider()
st.caption("Worldline / ULB · historical 2013 observations · Source labels ≠ model predictions · Values are transaction amounts, not measured financial losses.")
