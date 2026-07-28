# Atlas ROS v7.1.1 Initialization Performance Report

## Candidate-local deterministic measurement

The v7.1.1 benchmark executes 25 cold and 25 warm in-process Quick Initialization runs using deterministic read-only fixtures and the production warm-cache implementation.

| Metric | Cold | Warm |
|---|---:|---:|
| GitHub content reads per run | 3 | 1 |
| Live mutable Notion reads per run | 2 | 2 |
| Additional Todoist probes per run | 1 | 1 |
| In-process p50 | 0.0930 ms | 0.1517 ms |
| In-process p95 | 0.1753 ms | 0.2137 ms |
| Estimated compact fixture bytes | 3,243 | 2,536 |

Cold and warm contexts were canonically equivalent. Provider writes and Google Drive reads were zero.

The local warm path has negligible filesystem-authentication overhead and is not expected to outperform an all-memory fixture. Its material production benefit is eliminating two remote GitHub content round trips. Remote end-to-end p50 and p95 must be recorded in the attended final-candidate validation environment; this report does not fabricate connector latency.

## Acceptance targets for final-candidate evidence

- Warm Quick Initialization below 3 seconds where the supported production connector surface permits it.
- Cold Quick Initialization below 8 seconds.
- Warm path materially reduces remote connector round trips.
- No canonical result, module-count, permission, provider-write, or Google Drive-read regression.

## Cold CLI startup comparison

A separate 25-process local comparison used the exact v7.1.0 source package as baseline and the v7.1.1 candidate source with the same Python interpreter and environment.

| Metric | v7.1.0 baseline | v7.1.1 candidate |
|---|---:|---:|
| Wall-time p50 | 0.5518 s | 0.5805 s |
| Wall-time p95 | 0.5792 s | 0.6111 s |
| Atlas modules imported | 3 | 3 |
| Median maximum RSS | 109,620 KiB | 109,532 KiB |

The p95 ratio was approximately 1.055, within the existing 10% startup-regression allowance. Atlas module count did not regress, and ordinary `status` imported only `atlas_ros`, `atlas_ros.entry_points`, and `atlas_ros.entry_points.main`. Final CI measurements on Python 3.12 remain authoritative for candidate review.
