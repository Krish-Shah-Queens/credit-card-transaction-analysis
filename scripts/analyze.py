"""Run the SQL lessons, export aggregate CSVs, and create charts and findings."""
import argparse
import json
from pathlib import Path

import duckdb
import matplotlib
matplotlib.use("Agg")  # Works in terminals and continuous integration without a display.
import matplotlib.pyplot as plt

from common import DATABASE, REPORTS, ROOT

TEAL, ORANGE = "#007f86", "#c75a19"


def save_chart(figure, output, filename):
    figure.tight_layout()
    figure.savefig(output / filename, dpi=160, bbox_inches="tight")
    plt.close(figure)


def analyze(database=DATABASE, output=REPORTS):
    database, output = Path(database), Path(output)
    if not database.is_file():
        raise FileNotFoundError("Database missing. Run python scripts/build_database.py first.")
    output.mkdir(parents=True, exist_ok=True)
    tables = {}
    with duckdb.connect(str(database), read_only=True) as connection:
        for query_path in sorted((ROOT / "sql").glob("*.sql")):
            table = connection.execute(query_path.read_text(encoding="utf-8")).fetchdf()
            table.to_csv(output / f"{query_path.stem}.csv", index=False)
            tables[query_path.stem] = table
        quality = json.loads(connection.execute("SELECT report_json FROM data_quality").fetchone()[0])
    (output / "data_quality.json").write_text(json.dumps(quality, indent=2) + "\n", encoding="utf-8")
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})

    classes = tables["02_class_summary"]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(classes["label"], classes["transaction_count"], color=[TEAL, ORANGE])
    # Log scale keeps the rare fraud bar visible. Counts are also printed explicitly.
    ax.set_yscale("log")
    ax.set_ylabel("Transaction count (log scale)")
    ax.set_title("Labels are highly imbalanced")
    for i, row in classes.reset_index(drop=True).iterrows():
        if row.transaction_count:
            ax.text(i, row.transaction_count * 1.15, f"{row.transaction_count:,}", ha="center")
    ax.margins(y=0.2)
    save_chart(fig, output, "class_balance.png")

    hours = tables["03_elapsed_hours"]
    fig, axes = plt.subplots(2, 1, figsize=(9, 6), sharex=True)
    axes[0].bar(hours.elapsed_hour, hours.transaction_count, color=TEAL)
    axes[0].set_ylabel("Transaction count")
    axes[0].set_title("Activity during the observed two-day window")
    axes[1].plot(hours.elapsed_hour, hours.fraud_rate_pct, color=ORANGE, marker=".")
    axes[1].set_ylabel("Labeled fraud (%)")
    axes[1].set_xlabel("Elapsed hour since first transaction (last hour may be partial)")
    save_chart(fig, output, "elapsed_hours.png")

    bands = tables["04_amount_bands"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].bar(bands.amount_band, bands.transaction_count, color=TEAL)
    axes[0].set_ylabel("Transaction count")
    axes[1].bar(bands.amount_band, bands.fraud_rate_pct, color=ORANGE)
    axes[1].set_ylabel("Labeled fraud (%)")
    for ax in axes:
        ax.set_xlabel("Amount band (dataset units)")
        ax.tick_params(axis="x", rotation=25)
    fig.suptitle("Compare fraud rates with the size of each amount group")
    save_chart(fig, output, "amount_bands.png")

    rules = tables["07_threshold_tradeoffs"]
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(rules.threshold_amount, rules.precision_pct, "o-", color=TEAL, label="Precision")
    ax.plot(rules.threshold_amount, rules.recall_pct, "s-", color=ORANGE, label="Recall")
    ax.set(xlabel="Alert threshold (amount >= threshold)", ylabel="Percent", ylim=(0, 100),
           title="Amount-only rules miss many labeled fraud cases")
    ax.legend()
    save_chart(fig, output, "threshold_tradeoffs.png")

    kpi = tables["01_overview"].iloc[0]
    fraud_rows = classes.loc[classes.is_fraud == 1]
    labeled_amount = float(fraud_rows.total_amount.sum())
    top_decile_share = tables["05_amount_concentration"].iloc[0].share_of_total_amount_pct
    lines = [
        "# Credit Card Transaction Analysis — findings", "",
        "Source: ULB/Worldline 2013 dataset, obtained from TensorFlow's public CSV mirror.",
        f"Input SHA-256: `{quality['source_sha256']}`.", "",
        f"- Transactions: **{int(kpi.transaction_count):,}**; labeled fraud: **{int(kpi.fraud_count):,}** "
        f"(**{kpi.fraud_rate_pct:.4f}%**).",
        f"- Mean amount: **{kpi.mean_amount:,.2f}**; median: **{kpi.median_amount:,.2f}**; "
        f"maximum: **{kpi.maximum_amount:,.2f}** (dataset amount units).",
        f"- Total amount: **{kpi.total_amount:,.2f}**. Amount on fraud-labeled rows: "
        f"**{labeled_amount:,.2f}**. This is transaction value, not measured financial loss.",
        f"- The largest-amount decile accounts for **{top_decile_share:.2f}%** of total amount. "
        "This is a transaction-level measure; customers cannot be identified.",
        f"- Exact duplicate extra rows: **{quality['exact_duplicate_extra_rows']:,}**; "
        "retained because the source has no unique transaction identifiers.",
        f"- Zero-amount rows: **{quality['zero_amount_rows']:,}**; retained as valid source observations.",
        f"- Missing/non-finite rows: **{quality['missing_or_nonfinite_rows']:,}**; "
        f"negative time/amount rows: **{quality['negative_rows']:,}**; "
        f"invalid-label rows: **{quality['invalid_label_rows']:,}**.", "",
        "## Simple alert rules", "",
        "These in-sample descriptions are educational and do not establish predictive performance.", "",
        "| Threshold | Alerts | Labeled fraud caught | Precision % | Recall % |",
        "| ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rules.itertuples():
        precision = "undefined" if row.alert_count == 0 else f"{row.precision_pct:.4f}"
        recall = "undefined" if row.total_fraud == 0 else f"{row.recall_pct:.4f}"
        lines.append(f"| {row.threshold_amount} | {row.alert_count:,} | {row.true_positives:,} | {precision} | {recall} |")
    lines += ["", "![Label balance](class_balance.png)", "", "![Activity over time](elapsed_hours.png)",
              "", "![Amount bands](amount_bands.png)", "", "![Rule tradeoffs](threshold_tradeoffs.png)", "",
              "## Interpretation limits", "",
              "The observation period is about two days in 2013. Elapsed hour is not local clock time. "
              "These results do not support monthly trends, seasonal patterns, merchant comparisons, "
              "customer segmentation, or conclusions about today's card transactions. V1–V28 are "
              "anonymized PCA components, not identifiable customer attributes. Labels describe the "
              "source observations; an association does not establish a cause.", "",
              "Code and original documentation: MIT. External dataset: separate source terms; "
              "see ../../docs/DATASET.md. Raw data is not included in this repository.", ""]
    (output / "findings.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved {len(tables)} aggregate CSVs, 4 charts, quality checks, and findings to {output}")
    return tables


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, default=DATABASE)
    parser.add_argument("--output", type=Path, default=REPORTS)
    args = parser.parse_args()
    try:
        analyze(args.database, args.output)
    except (OSError, ValueError, duckdb.Error) as error:
        parser.exit(1, f"Analysis failed: {error}\n")
