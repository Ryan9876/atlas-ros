# Release Control Center

The Release Control Center is a read-only, self-contained dashboard generated from a Release Validation Workbench JSON report.

It presents release identity, active and rollback authority, gate status, blockers, artifact checksums, report fingerprints, candidate readiness, and promotion boundaries.

It cannot create a Candidate, authorize promotion, edit release authorities, or promote a release.

## Build

```bash
PYTHONPATH=src python scripts/build_release_control_center.py validation-output/<run>/validation-report.json --output release-control-center
```

The command exits `0` only when the evidence is candidate-ready and `2` when blocked.
