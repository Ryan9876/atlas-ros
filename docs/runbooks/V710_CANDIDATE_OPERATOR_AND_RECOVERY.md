# Atlas ROS v7.1.0 Candidate Operator and Recovery Runbook

Status: Candidate guidance only. Atlas ROS v7.0.1 remains Active.

## Candidate validation

1. Validate GitHub-first current authority and rollback identities.
2. Run Ruff, architecture validation, legacy isolation, strict MyPy, complete branch-aware tests, dependency policy, secret scan, PyPI and OSV audits.
3. Compile corrective, minor, and major release fixtures and compare deterministic receipts.
4. Prove zero current Drive dependencies and run non-destructive retirement simulation.
5. Validate historical cleanup dry-run, authorization rejection, idempotency, partial failure, and readback.
6. Build source and wheel once, install cleanly, and verify candidate runtime identity while reporting Active production remains v7.0.1.
7. Validate startup import, wall-time, and memory gates.
8. Restore immutable v7.0.1, v6.5.0, and v6.2.0 packages.
9. Produce checksums, SBOM, source manifest, exact candidate identity, and Full Validation evidence.

## Stop conditions

Stop on authority disagreement, current Drive dependency, unclassified retention item, production import from migration/release/legacy packages, compiler nondeterminism, failed clean install, failed restoration, security finding, performance regression above the gate, or any provider write.

## Recovery

Discard the candidate branch or restore from the exact prior commit. No production rollback is necessary because candidate work does not change Active authority. If later promoted under separate authorization, use the active manifest and System State to execute the governed rollback transaction to v7.0.1.
