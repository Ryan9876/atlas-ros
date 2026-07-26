# ADR-010: Semantic Intent Separation and Output Fidelity

Status: Accepted for Atlas ROS v6.1.0 development

Date: 2026-07-26

## Context

Side-by-side processing of the Arista CloudVision code-upgrade automation pilot showed a semantic regression across Atlas ROS v5.4 through v6.0. The system became more deterministic and auditable, but benchmark controls, version-comparison instructions, transaction evidence, and reconciliation receipts progressively displaced the user's primary business outcome in Todoist.

The v6 orchestration and reconciliation layers applied and verified the approved plan correctly. The defect originated upstream because `normalized_intent`, unstructured `known_inputs`, management completion evidence, and execution-candidate extraction did not preserve a first-class boundary between business work and control-plane evidence.

## Decision

Atlas ROS v6.1.0 introduces versioned semantic contracts:

- `IntentPartitionV1`
- `ReasoningPackageV4`
- `ManagementPackageV3`
- `ExecutionCandidateV3`
- `ProjectionDecisionV3`
- `ExecutionPlanV3`
- `SemanticFidelityResultV1`

Every instruction is assigned one semantic role. Only a parent business outcome and qualifying current Ryan-owned business actions may become execution objects. Delegated, conditional, evaluation, audit, provider-control, and reference content remains in governed management evidence unless the user explicitly makes it the primary business outcome.

A separate Semantic Fidelity Gate blocks orchestration when the parent does not preserve the primary outcome, the minimum current path is missing, control-plane content leaks into execution, delegation is violated, the horizon is premature, or intent remains unresolved.

## Consequences

- Benchmark controls may alter duplicate handling, audit records, authorization evidence, readback, and reconciliation receipts, but cannot alter the business execution plan.
- Controlled technology pilots use a reusable planning model with one parent and three current management checkpoints.
- Existing v6 orchestration and reconciliation contracts remain compatible and provider-neutral.
- v6.0.0 remains production authority throughout development and becomes rollback only after an explicitly authorized v6.1.0 promotion.
- Historical v5.2 through v6.0 records remain unchanged.

## CloudVision gold

Parent:

> Launch the Arista CloudVision code-upgrade automation pilot

Current checkpoints:

1. Define and approve pilot scope and success measures.
2. Assign the technical owner and confirm low-risk pilot targets.
3. Approve pre-checks, change controls, evidence requirements, and rollback plan.

Technical execution remains delegated and evidence review remains conditional.
