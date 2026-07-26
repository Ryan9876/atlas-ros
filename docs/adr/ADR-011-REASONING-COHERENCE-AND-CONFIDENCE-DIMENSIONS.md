# ADR-011: Reasoning Coherence and Confidence Dimensions

- Status: Accepted for Atlas ROS v6.1.1 development
- Date: 2026-07-26
- Decision owner: Ryan Smith
- Related review: V4V-39 — Arista CloudVision Pilot v6.1 Full Benchmark Acceptance Test
- Related initiative: Atlas ROS v6.1.1 Reasoning Coherence Remediation

## Context

Atlas ROS v6.1.0 restored semantic fidelity for controlled technology pilots. The CloudVision benchmark produced the correct parent outcome and three current Ryan-owned checkpoints, retained technical execution as delegated work, retained evidence review as conditional work, and excluded comparison and audit evidence from Todoist.

The same Reasoning Package nevertheless reported contradictory metadata: the governed planning model was selected at high confidence, no human decision was required, and semantic fidelity passed, while legacy classification fields reported low confidence, unresolved responsibility, a `Needs Clarification` workstream, and clarification-required language.

This contradiction did not alter the execution plan, but it made the explanation and downstream metadata untrustworthy.

## Decision

Atlas ROS will represent confidence as explicit dimensions and will validate the dimensions through a deterministic, provider-independent Reasoning Coherence Gate before management-plan approval.

### Confidence dimensions

At minimum, Atlas will represent:

- intent partition confidence
- planning-model confidence
- classification confidence
- responsibility-resolution confidence
- routing confidence
- semantic-fidelity confidence when a scored semantic result is used

Each dimension records its subject, evidence basis, whether it affects execution eligibility, whether it requires attended review, and its relationship to the other dimensions. Atlas will not use one blended score to hide material uncertainty.

### Coherence invariant

The execution decision, review state, confidence dimensions, classification metadata, responsibility metadata, routing result, management plan, semantic-fidelity result, and user-facing explanation must describe the same governed conclusion.

### Fail-closed conditions

A contradiction is material and review-blocking when it can affect:

- responsibility or ownership
- routing or destination
- execution readiness
- provider-object eligibility
- user guidance about whether clarification is required

A non-operational metadata gap may remain non-blocking only when it is explicitly identified, semantically independent, and explained accurately.

### Controlled technology pilots

The `controlled-technology-pilot` planning model will supply governed responsibility and workstream evidence for controlled infrastructure and automation pilots without vendor-specific exceptions. The model may resolve the responsibility domain and workstream when the request is otherwise sufficiently specific and the selected model is high confidence.

### Compatibility

Atlas ROS v6.1.1 will preserve existing v6.1 contracts and meanings. New versioned coherence contracts and compatibility adapters may supplement existing fields. Existing consumers will continue to receive the original fields, but those fields must be populated consistently with the new coherence result.

### Benchmark lifecycle

Provider-free semantic benchmarking is the default. Shadow orchestration may produce plans, commands, journals, and receipts without provider writes. An attended provider canary requires an explicit object budget and authorization.

Version-specific benchmark evidence should normally be stored in Review Records linked to durable operational records rather than creating duplicate production projects. A dedicated Benchmark Runs collection requires a separate schema and authority decision.

### Horizon promotion

Horizon re-evaluation is deterministic and provider-free. It may propose a transition, but no Todoist or Notion provider object may be created or modified without separate attended authorization.

## Consequences

- Contradictory reasoning metadata becomes release-blocking when material.
- User-facing explanations accurately identify any low-confidence dimension and its operational effect.
- CloudVision and equivalent Cisco, monitoring, proof-of-concept, and controlled infrastructure trials use the same governed model logic.
- The approved CloudVision parent and three checkpoints remain unchanged.
- No integration permissions, provider-write scope, autonomy level, calendar, messaging, email, deletion, or scheduling authority changes.

## Validation requirements

- Reasoning Coherence benchmark: 100%
- CloudVision metamorphic family: 100% invariant
- no contradictory explanation cases
- no material unresolved responsibility passing without review
- provider-free and shadow modes: zero provider writes
- existing semantic, planning, orchestration, reconciliation, compatibility, restoration, packaging, security, and rollback gates remain green
