# ADR-0080 — Capability-Scoped Runtime Composition

## Status

Proposed for v7.4.5 candidate validation.

## Decision

After command selection, Atlas may compose only the declared contracts, policies, schemas, ports, adapters, and capabilities required by that command. The dependency graph is machine-readable and digest-bound.

Composition broadens to the full runtime when declarations are incomplete, metadata is inconsistent, execution or authorization infrastructure is involved, restoration or migration is involved, policy marks broad impact, or release validation requires it.

Scoped composition cannot bypass policy, evidence, write safeguards, or command semantics. Candidate validation must prove externally observable equivalence between scoped and full composition for every supported command.
