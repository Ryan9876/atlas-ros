# ADR-004: Canonical Contracts and Compatibility Architecture

Status: Accepted for development. Production activation remains Ryan-only.

## Context

Atlas ROS currently exposes behavior through W-numbered workflow modules. Those modules combine historical naming, orchestration, domain decisions, and provider concerns. The capability-based architecture requires stable semantic contracts before components can be separated without behavioral drift.

## Decision

Atlas ROS will use immutable, versioned canonical contract envelopes for communication between capabilities:

- Capture Envelope
- Reasoning Package
- Knowledge Package
- Management Package
- Execution Plan
- Execution Receipt
- Reconciliation Result

Contract version 1 is additive and does not replace existing production models. Existing W01, W02, W03A, and W03 interfaces remain available through explicit compatibility facades that delegate to the current production services.

## Dependency rules

1. Contracts contain data and invariants only.
2. Contracts cannot import workflows, legacy facades, or provider adapters.
3. Engines, planning, and policy layers cannot import provider adapters or legacy facades.
4. Provider adapters cannot decide whether an execution object should exist.
5. Legacy facades may depend on existing workflows during the compatibility period.
6. Architectural boundary validation is release-blocking in CI.

## Contract invariants

- Applied execution receipts require successful readback verification.
- Reconciliation checkpoints cannot advance while mismatches exist.
- Execution steps use deterministic contiguous one-based ordering.
- Contract objects reject unknown fields and are immutable after creation.
- Provider-specific metadata is isolated in explicitly named fields.

## Compatibility policy

The W convention remains supported until semantic workflows have completed differential validation and at least one stable compatibility release has been promoted. Retirement requires:

- identical externally observable behavior;
- migration and rollback evidence;
- no unresolved consumer dependencies;
- explicit Ryan promotion authorization.

## Consequences

The new contracts become the stable internal seam for subsequent capability extraction. Wave 1 introduces no production workflow change, no new integration scope, and no autonomous action. Temporary duplication between legacy models and canonical envelopes is accepted to enable measured migration.
