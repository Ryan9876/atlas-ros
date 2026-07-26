# ADR-012: Adaptive Input Processing and Planning Graph

- Status: Proposed for Atlas ROS v6.2.0
- Date: 2026-07-26
- Decision owner: Ryan
- Implementation authority: Atlas under the active delegated-development decision
- Supersedes: no historical ADR; extends ADR-010 and the v6.1.1 Reasoning Coherence controls

## Context

Atlas ROS v6.1.1 restored a correct business-centered CloudVision plan and made the planning model, responsibility domain, workstream, clarification state, and user explanation coherent. The prior v6.1.0 acceptance test demonstrated that correct task projection alone was insufficient: high-confidence model selection could coexist with low-confidence or unresolved legacy metadata. The v6.1.1 coherence gate corrected that defect, but input processing remained primarily a semantic partition followed by a linear management projection.

The next architecture must support broader and more complex inputs without weakening provider separation, attended execution, fail-closed behavior, deterministic replay, canonical reconciliation, or historical rollback.

## Decision

Atlas ROS v6.2 introduces a provider-free adaptive input-processing pipeline with fourteen integrated capabilities:

1. multidimensional intent confidence;
2. a typed intent graph;
3. explicit dependency discovery;
4. a governed planning-archetype registry;
5. business-intent and domain-knowledge separation;
6. typed constraint propagation;
7. canonical intent compression;
8. high-value clarification selection;
9. presentation-only planning-style recognition;
10. a structured reflection gate;
11. multidimensional inherent and residual risk;
12. multi-outcome recognition;
13. governed planning memory;
14. adaptive minimum-path projection.

The canonical stage order is:

1. raw capture;
2. input normalization;
3. canonical intent compression;
4. multi-outcome recognition;
5. business-intent partitioning;
6. domain-pack selection;
7. archetype selection;
8. graph construction;
9. dependency discovery;
10. constraint propagation;
11. confidence profiling;
12. governed-memory consultation;
13. management structure;
14. dynamic risk evaluation;
15. adaptive projection;
16. clarification/review decision;
17. reflection and coherence validation;
18. Enhanced Reasoning Package V5;
19. provider-free execution planning;
20. attended authorization;
21. provider application only after separate authorization;
22. readback and canonical reconciliation.

## Architectural boundaries

### Reasoning remains non-executing

The v6.2 engines cannot import provider adapters, construct canonical execution plans or receipts, authorize operations, read provider credentials, or perform provider writes. The Enhanced Reasoning Package records `provider_writes = 0` and `execution_authorized = false` as literal contract values.

### Business truth is independent of presentation

Planning style may change wording and detail only. It cannot change the canonical intent fingerprint, graph, responsibility, workstream, risk, authorization state, or projected node identities.

### Domain knowledge is nonauthoritative

Domain packs are versioned, replaceable, provider-free, and execution-ineligible. A domain pack may contribute terminology and planning facts. It may not decide that provider execution is permitted. Missing domain knowledge lowers confidence and may trigger clarification instead of fabricated technical detail.

### Archetypes suggest topology but do not override intent

The archetype registry is declarative and versioned. Selection is evidence-based and confidence-scored. Archetypes may propose a management topology only after canonical intent and outcome recognition. New archetypes or topology patterns require governed approval and benchmark evidence; there is no silent online learning.

### Planning memory is advisory

Planning memory stores approved topology, policies, failure patterns, and benchmark outcomes—not unrestricted user content. Every memory entry requires provenance, version, scope, approval state, and a review or expiry policy. Memory cannot override live authority or explicit user intent.

### Graph projection is selective

Only current business nodes may be projection eligible. Dependencies, constraints, assumptions, risks, approvals, evidence requirements, domain references, delegated outcomes, conditional outcomes, future outcomes, and control-plane records remain outside the user-facing execution provider unless separately made eligible by explicit policy and authorization.

## Data contracts

The architecture adds versioned contracts for:

- `CanonicalIntent`;
- `OutcomeSet` and `OutcomeV2`;
- `IntentGraph`, `IntentNode`, and `IntentEdge`;
- `DependencyRecord`;
- `ConstraintRecord` and `ConstraintPropagationResult`;
- `PlanningArchetype` and `ArchetypeSelection`;
- `IntentConfidenceProfile` and `ConfidenceDimensionV2`;
- `DomainKnowledgePackV62`, selection, and context;
- `ClarificationDecision`;
- `RiskProfile` and `RiskDimension`;
- `ReflectionResult` and `ReflectionFinding`;
- `PlanningMemoryEntry`;
- `ProjectionPolicy` and `ProjectionDecisionV62`;
- `EnhancedReasoningPackageV62` with contract version 5.

All material contracts are immutable Pydantic models with forbidden extra fields, stable serialization, SHA-256 digests, explicit version fields, and fail-closed model validators.

## Confidence policy

A single aggregate score may be shown for convenience, but it cannot hide a failing material dimension. The profile includes business objective, intent type, responsibility, routing, current horizon, delegation, dependency completeness, constraint completeness, temporal scope, domain sufficiency, ambiguity resolution, contradiction resolution, and execution eligibility.

A material dimension below its configured threshold blocks execution eligibility or requires attended review. High-confidence planning-model selection cannot coexist with unresolved responsibility or `Needs Clarification` routing.

## Constraint policy

Constraints retain their source, strength, affected nodes, and derived effects. Hard constraints propagate through sequencing, risk, dependency readiness, and projection. Incompatible hard constraints or a request to bypass the provider authorization boundary fail closed.

## Clarification policy

The clarification engine asks only the highest-value material question. It distinguishes:

- clarification required;
- human review required;
- optional enrichment;
- nonblocking warning;
- no clarification required.

No question is asked when the current business plan is materially coherent. A clarification state and the user-facing explanation may not contradict each other.

## Reflection policy

Reflection emits structured findings—not private chain-of-thought. It checks primary-outcome visibility, control-plane exclusion, delegation integrity, horizon integrity, routing coherence, hard-constraint satisfaction, graph integrity, and minimum-path projection. Findings are classified as blocking, review-required, warning, or informational. Revisions are deterministic and bounded to two passes.

## Risk policy

Risk profiles distinguish inherent and residual risk for business, operational, planning, execution, dependency, constraint, change, security/compliance, rollback, evidence, ambiguity, and provider-write dimensions. Risk can require clarification or human review; it never authorizes execution.

## CloudVision critical regression contract

The input `Task = arista cloud vision code upgrade automation pilot.` must continue to produce:

Parent:

- Launch the Arista CloudVision code-upgrade automation pilot

Current checkpoints:

1. Define and approve pilot scope and success measures.
2. Assign the technical owner and confirm low-risk pilot targets.
3. Approve pre-checks, change controls, evidence requirements, and rollback plan.

Withheld:

- delegated technical implementation;
- conditional evidence review and go/no-go decision;
- future expansion;
- benchmark comparisons, duplicate exceptions, journals, receipts, hashes, authorization identities, checkpoints, and preservation evidence.

Required metadata remains `controlled-technology-pilot`, `project_delivery`, `Active Projects`, no clarification, no human review, and zero provider writes.

## Security and privacy consequences

Positive consequences:

- less fabricated technical detail when domain knowledge is missing;
- explicit contradiction and constraint gates;
- no hidden learning or self-modification;
- provenance and digests for memory, archetypes, domain packs, and reasoning outputs;
- no provider identifiers or credentials in reasoning contracts;
- bounded, inspectable reflection findings.

Costs and risks:

- increased contract and benchmark surface;
- higher processing latency and memory use;
- more schema-migration responsibility;
- potential over-gating if confidence thresholds are poorly calibrated;
- risk of archetype bias if registry governance weakens.

These risks are controlled through deterministic benchmarks, performance thresholds, additive schema evolution, versioned registries, Full Validation, and an immutable v6.1.1 rollback.

## Migration

Reasoning Package V4 remains readable. V6.2 adds a new contract version rather than modifying historical records. Lossy projection back to older contracts is allowed only when the package is execution eligible, has no material graph conflict, and does not depend on v6.2-only multi-outcome, constraint, memory, or risk semantics. Otherwise migration fails closed.

## Release decision

This ADR authorizes implementation and release-candidate validation only. Final merge, immutable tag creation, GitHub Release publication, Release Index or System State changes, and rollback replacement remain reserved for a separate explicit Ryan authorization.
