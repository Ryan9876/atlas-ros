# Atlas ROS v6.0.0 Promotion Retry 1

The first final-publication run `30144677820` created the final release and uploaded the staged
assets, but failed closed during the combined readback/restoration step. No production authority
record was changed.

The controller was hardened in commit `8a8d3ed01d8658c0606790662463803f224b8f2f` to separate:

1. final asset download and checksum verification;
2. Drive-independent restoration and release benchmarks; and
3. final tag metadata and exact-target verification.

This retry remains bound to:

- exact candidate `3961d4880b3ed7542314d91b79c6b4780c0952f1`;
- candidate package SHA-256 `147aa08e3d60e17cf6b3f25099b3d00080e954b0a78cf7971bc08c58fa78bf63`;
- Full Validation `V4V-34`;
- promotion decision `V4D-29`; and
- immutable rollback Atlas ROS v5.6.0 at production source
  `06c5a703dec72135171d5738e6e0f3573ed8499d`.

Authority records may switch only after every separated retry gate passes.
