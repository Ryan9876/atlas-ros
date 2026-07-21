# Atlas ROS v4.5.2 Remediation Matrix

## Critical
- C-01: Remediated — code-bearing source distribution, wheel, manifest, checksums, SBOM, validation report, and review sign-off produced.
- C-02: Remediated — YAML policy files ship inside `atlas_ros.data`; clean-wheel smoke test passes.
- C-03: Remediated — W03 validates content, creates/repairs parent and ordered subtasks, and performs full-field readback.
- C-04: Remediated — command mutations are grouped; processed state is recorded only after every mutation and readback succeeds; failed groups remain retryable.
- C-05: Remediated — plan captures a read snapshot before provider reads and advances only to that snapshot after successful application.

## High
- H-01/H-02/H-03: Remediated — all governed risk commands and Execution Step priority/state/completion fields are synchronized. Section and label constraints are validated in W03 and retained in readback.
- H-04/H-05/H-06: Remediated — existing mappings update in place, requested properties are compared on readback, and adapter errors follow the same missing-object path as test doubles.
- H-07/H-08: Remediated — W01 capture and outbox insert share one transaction; SQLite busy timeout, WAL, and durable state are enabled.
- H-09/H-10: Remediated — exact dev-tool versions, version 4.5.2 metadata, artifact smoke testing, and current release documentation are provided.
- H-11/H-12: Remediated — 429 is retryable, responses are normalized/redacted, provider-host overrides are blocked by default, and production-shaped fault tests were added.
- H-13: Remediated — explicit clarification flags route to clarification regardless of confidence.
- H-14: Remediated in candidate evidence — executable artifacts and complete validation evidence are included.

## Medium
M-01 through M-22 were addressed through idempotent command groups, redacted provider failures, base-URL controls, normalized JSON errors, Pydantic constraints, ambiguous-delegate conflicts, deterministic pattern selection, isolated immutable configuration, runtime-injected data-source IDs, stronger model validation, safe checksum paths, candidate provenance/SBOM evidence, SQLite migration versioning and file permissions, atomic outbox export, reduced duplicate reads, decomposed helper validation, concrete observability tests, pinned compatibility versions, and idempotency regression tests.

Production signing remains an organizational release control: a governed private signing key must be selected by the release owner. GitHub Actions are pinned to immutable full commit SHAs. The candidate does not embed or generate private signing material.
