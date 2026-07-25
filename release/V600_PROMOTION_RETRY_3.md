# Atlas ROS v6.0.0 Promotion Retry 3

Run `30144897820` verified the final release assets, final wheel installation, runtime semantic-only
surface, and restored planning, orchestration, and reconciliation benchmarks. It failed closed only
because the W-retirement inventory scanned the deliberately bundled immutable v5.6 rollback source
as if it were active v6 source.

The scope boundary was corrected through:

- inventory implementation commit `cd214092f164458d05b861213c2c0e8380cd7214`;
- source-distribution exclusion commit `1c60bed00ae64306c23bd23f757392693658f3f1`;
- regression-test commit `2e1f33caabc866ee48499689befd22f99c7ee614`; and
- final-controller commit `abc8b697fc5c029e5d97ebf640c3f1f6f94482e7`.

The corrected inventory excludes only the immutable `rollback-source` evidence tree and continues
to fail on any W-number module or direct legacy/workflow reference in active v6 source. This retry
remains bound to exact candidate `3961d4880b3ed7542314d91b79c6b4780c0952f1`, package SHA-256
`147aa08e3d60e17cf6b3f25099b3d00080e954b0a78cf7971bc08c58fa78bf63`, Full Validation
`V4V-34`, promotion decision `V4D-29`, and immutable rollback Atlas ROS v5.6.0.
