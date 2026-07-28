# ADR-014 — Version-Neutral Release Compiler

## Status

Accepted for the Atlas ROS v7.1.0 candidate.

## Context

Release-family scripts duplicated policy and embedded release numbers, which increased activation drift risk. Candidate validation, publication, and authority activation must remain separate and exact.

## Decision

A single declarative Release Specification is the source for deterministic candidate artifacts. The compiler produces manifest, scope, notes scaffold, authority candidate, Release Index candidate, checksum inventory, source manifest, SBOM references, validation, publication, activation, restoration and rollback plans, transaction identities, and receipts.

The compiler:

- is semantic-version neutral;
- requires immutable commit identities and exact rollback identities;
- requires GitHub, Notion, and Todoist exactly as production integrations;
- treats Drive only as optional historical access;
- enforces build-once, independent readback, and rollback restoration prerequisites;
- emits candidate-only artifacts with production authorization, publication, activation, and provider writes set to false or zero;
- never publishes or changes authority.

Release-family wrappers may remain temporarily only when they invoke the canonical compiler, contain no independent policy, are visibly deprecated, and have tests and removal conditions.
