# Contributing

New learners are welcome. Good first contributions include a clearer SQL comment, a small explanation of a chart, or a practice question with an independently checked answer.

1. Open an issue describing a bug or proposed improvement, or choose an existing issue.
2. Fork the repository and create a branch: `git switch -c improve-sql-explanation`.
3. Create a virtual environment and install `requirements-dev.txt`.
4. Make a focused change and update the relevant documentation.
5. Run `python -m pytest -q`. If analysis or queries changed, rerun the full pipeline and check the outputs.
6. Open a pull request explaining the result, why it helps, and how you checked it.

Keep raw data, local databases, credentials, and virtual environments out of commits. Do not add real card numbers or customer details. Use small hand-authored fixtures for pipeline tests. Keep source attribution when discussing dataset-derived findings. Add tests when a change affects data validation or calculation correctness.

Contributions to code and original documentation are provided under the repository's MIT license. Dataset terms remain separate. Be patient and respectful when reviewing work, explain your reasoning, and welcome questions.
