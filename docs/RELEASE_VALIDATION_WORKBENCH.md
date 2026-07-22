# Release Validation Workbench

The Release Validation Workbench executes Atlas ROS release gates in a fixed order and emits reproducible evidence. It does not create a Candidate, authorize promotion, modify production authority, or waive missing gates.

## Run

```bash
python scripts/run_release_validation.py --release-id "Atlas ROS v5.0" --package
```

A blocked run exits with status 2. A fully validated run exits with status 0.

## Evidence

Each run produces command logs, JSON and Markdown reports, SHA-256 checksums, a report fingerprint, and an optional deterministic evidence archive.

Manual gates, including independent review, remain `not_run` unless explicit evidence references are provided through a JSON file passed with `--manual-evidence`.
