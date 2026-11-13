# Educational fraud detector

## Source labels and predictions

The ULB CSV's **Class** is the existing target: `1` denotes a fraud label, `0` a non-fraud label. The original 284,807-row source has 492 fraud labels. The dashboard preserves them as `is_fraud`; it does not decide or retrospectively change those labels. The source does not provide each case's investigative history.

The added model outputs a **score** and a separate **flag for review**. Scores are **not calibrated fraud probabilities**. A score of 0.972 does not establish a 97.2% real-world chance of fraud. Flags are predictions evaluated against the original labels, not confirmed cases.

## Features and data handling

- Inputs: V1–V28 plus `log1p(Amount)`, 29 numerical features.
- Excluded inputs: `Class`, source time, and local identifiers.
- Exact source duplicates removed for modeling: 1,081. Descriptive analysis retains all original rows.
- Remaining modeling observations: 283,726, including 473 fraud labels.
- Split: source time quantiles at 60% and 80%; equal timestamps remain in one split.
- No random train/test mixing or pre-split oversampling.

| Split | Observations | Fraud labels | Elapsed seconds |
| --- | ---: | ---: | --- |
| Train | 170,235 | 342 | 0–120,392 |
| Validation | 56,745 | 57 | 120,393–145,233 |
| Test | 56,746 | 74 | 145,234–172,792 |

V1–V28 must use the same PCA representation as the source. The original transformation and original feature meanings are unavailable. Arbitrary card records cannot be scored from amount and time alone. Source PCA transformation predates this project; any possible information used during that original transformation cannot be controlled here.

## Training and selection

Two candidates were fit on training data: balanced logistic regression with training-only standardization, and balanced histogram gradient boosting. Selection used **validation average precision**, not test results:

| Candidate | Validation average precision |
| --- | ---: |
| Logistic regression | 0.753208 |
| Histogram gradient boosting | 0.755399 |

Histogram gradient boosting was selected. The fixed threshold grid is 0.000–1.000 in steps of 0.001, with inclusive `score >= threshold` semantics. The default threshold **0.972** maximizes validation F2; ties choose the higher threshold. F2 emphasizes recall and is an educational objective, not a financial cost model. No test-based threshold selection or refitting on validation/test observations was performed.

## Later-period test results

At the validation-selected threshold:

| Measure | Value |
| --- | ---: |
| True positives | 54 |
| False positives | 10 |
| False negatives | 20 |
| True negatives | 56,662 |
| Model alerts | 64 |
| Precision | 84.375% |
| Recall | 72.973% |
| Average precision over ranked test scores | 0.797910 |

An always-non-fraud baseline would be about 99.87% accurate on this test set while missing all 74 fraud labels. This is why accuracy alone is inadequate. Moving the app's threshold slider explores the same holdout repeatedly; those alternate points are descriptive exploration, not new unbiased evaluations.

## Limitations

This is a small historical benchmark from about two days in 2013. A chronological holdout is stronger than training-set evaluation, but it does not establish performance on modern real-world transactions. Validation contains only 57 positive labels, so model selection and threshold estimates can be unstable. The selected model's validation advantage is small. No confidence bounds or guarantee of superiority over other models is claimed.

Customer overlap across splits cannot be measured because customer identifiers are absent. Anonymized PCA values cannot support meaningful customer or merchant explanations. No causal explanation for a source label is available. There is no production monitoring, human adjudication, or live transaction integration.

## Reproduce and inspect

```bash
python scripts/download_data.py
python scripts/build_database.py
python scripts/train_fraud_model.py
```

The training script saves `models/fraud_detector.joblib` and `dashboard/data/model_evaluation.json`. The report includes source hash, feature order, preprocessing, split boundaries, validation results, threshold-selection rule, test confusion counts at every grid point, and artifact hash. The app verifies the committed model's hash before loading it. Only the known project artifact is loaded; upload files are feature CSVs, not serialized models.

Code is MIT; the dataset-derived report and selected held-out examples retain the external data's ODbL/DbCL terms and source attribution. The detector is an educational example, not a payment authorization or confirmed-fraud service.
