# Startup Performance Report — v7.1 Candidate

The validation workflow measures cold `atlas status --json` startup wall time, Atlas module import count, and process maximum RSS over repeated subprocess runs. Candidate results are compared with immutable v7.0.1. The gate allows no Atlas module-count regression and no more than 10% p95 startup regression.

Release, migration, scenario, and provider modules are excluded from ordinary status command loading. Final measured values are retained in candidate evidence; this document does not fabricate measurements before CI runs.
