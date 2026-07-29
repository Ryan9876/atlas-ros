# v7.3 GitHub Actions Cost Optimization

## Controls

- One draft implementation PR.
- Dedicated lean draft workflow with path filters and stale-run cancellation.
- Existing broad PR CI is skipped for the v7.3 branch.
- Full CI runs only on `ready_for_review` or explicit dispatch.
- Routine checkout is shallow; release/rollback validation uses full history.
- Frozen candidate artifacts are built once and reused downstream.
- Routine artifacts retain 7 days; governed candidate evidence retains 90 days.

Run counts, durations, cache evidence, cancellations, artifact IDs, and compute-time comparisons are populated from actual workflow readback. Monetary savings are intentionally not estimated without billing data.
