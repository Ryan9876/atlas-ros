# Atlas ROS v6.2 Adaptive Input-Processing Architecture

## Purpose

Atlas ROS v6.2 converts short, ambiguous, multi-outcome, or constraint-heavy input into an inspectable provider-free reasoning package. It does not execute work. It prepares a governed, minimum coherent current path that may later be handed to the canonical planner and attended execution boundary.

## Pipeline

| Stage | Input | Output | May write providers? |
|---|---|---|---|
| Capture | Raw user input | Immutable raw text | No |
| Canonicalization | Raw text | `CanonicalIntent` and semantic fingerprint | No |
| Outcome recognition | Canonical intent | `OutcomeSet` | No |
| Domain composition | Canonical domain | Versioned `DomainKnowledgeContextV62` | No |
| Archetype selection | Canonical intent | `ArchetypeSelection` | No |
| Dependency discovery | Archetype + domain | `DependencyRecord[]` | No |
| Constraint propagation | Raw constraints + graph targets | `ConstraintPropagationResult` | No |
| Graph construction | Outcomes, dependencies, constraints | `IntentGraph` | No |
| Confidence | All semantic evidence | `IntentConfidenceProfile` | No |
| Memory consultation | Approved topology memory | Referenced memory IDs only | No |
| Risk | Graph and controls | `RiskProfile` | No |
| Clarification | Confidence, risk, conflicts | `ClarificationDecision` | No |
| Projection | Eligible current business nodes | `ProjectionDecisionV62` | No |
| Reflection | Graph, routing, projection | `ReflectionResult` | No |
| Packaging | All prior outputs | `EnhancedReasoningPackageV62` | No |

Provider application remains downstream of a separate execution plan, attended authorization, immutable command, readback, receipt, and reconciliation transaction.

## Stable identity

V6.2 uses SHA-256 identities for:

- canonical semantic intent;
- outcome sets;
- archetype selections;
- domain packs and domain selection;
- intent graphs;
- constraint propagation;
- confidence profiles;
- risk profiles;
- clarification decisions;
- reflection results;
- planning-memory content;
- projection decisions;
- the final Enhanced Reasoning Package.

Identical inputs, registries, policies, and memory state must produce identical outputs and fingerprints. Presentation style is deliberately excluded from the canonical semantic fingerprint.

## Intent graph

### Node types

- primary outcome;
- secondary outcome;
- current checkpoint;
- delegated outcome;
- conditional outcome;
- future outcome;
- dependency;
- constraint;
- assumption;
- risk;
- approval;
- evidence requirement;
- domain-knowledge reference.

### Edge types

- requires;
- enables;
- blocks;
- depends on;
- delegated to;
- conditional on;
- constrained by;
- evidenced by;
- precedes;
- refines;
- conflicts with;
- derived from.

Graph validation rejects duplicate IDs, invalid references, self-cycles, and material dependency cycles. Material orphan findings block projection. The graph remains provider neutral and contains no provider object IDs.

## Projection eligibility

Only these node types may be eligible:

- primary outcome;
- secondary outcome;
- current checkpoint.

They must also be on the current horizon. Delegated, conditional, future, reference, risk, dependency, constraint, audit, and control-plane nodes are always withheld by the v6.2 reasoning layer.

Complexity bands govern the maximum current checkpoint depth:

- small: up to 2;
- medium: up to 5;
- large: up to 8;
- program: up to 12.

The parent outcome is projected with the bounded current checkpoints. The number is derived from the graph rather than a universal fixed task count.

## Confidence dimensions

The minimum v6.2 profile contains:

1. primary business objective;
2. intent type;
3. responsibility domain;
4. workstream routing;
5. current horizon;
6. delegation;
7. dependency completeness;
8. constraint completeness;
9. temporal scope;
10. domain-knowledge sufficiency;
11. ambiguity resolution;
12. contradiction resolution;
13. execution eligibility.

A material floor is calculated from all material dimensions. A dimension can be low and nonblocking only when it is explicitly marked nonmaterial and excluded from execution eligibility. The overall state cannot conceal a failing material dimension.

## Dependency states

- `confirmed`: directly supported by authoritative or explicit evidence;
- `inferred`: required by a governed archetype with adequate evidence;
- `optional`: useful but not required for the current outcome;
- `unresolved`: material readiness or identity is unknown.

A dependency is not automatically a task. It becomes a current task only when it is current, user-owned, independently executable management work. Otherwise it remains a graph dependency and influences confidence or risk.

## Constraints

Constraints are typed as hard constraints or preferences. Supported categories include availability, safety, security, compliance, budget, timeline, resource capacity, scope, environment, approval, rollback, evidence, change management, provider restrictions, and user prohibitions.

Every constraint retains:

- original statement;
- source;
- strength;
- affected nodes;
- derived effects;
- conflicts.

Hard conflicts fail closed and produce no current projection.

## Archetype registry

The registry is stored in `src/atlas_ros/data/planning_archetypes_v1.json`. Initial approved archetypes are:

- controlled technology pilot;
- infrastructure modernization;
- operational remediation;
- migration;
- decommission;
- automation proof of concept;
- compliance readiness;
- vendor evaluation;
- process improvement;
- incident follow-up.

The registry is advisory. Explicit input takes precedence. Registry changes require code review, benchmark evidence, and a governed decision.

## Domain packs

Domain packs are stored in `src/atlas_ros/data/domain_packs_v1.json`. They separate provider-neutral technical vocabulary and planning facts from domain-independent business reasoning. Packs are selected after canonical intent is established.

Each pack is:

- versioned;
- immutable inside a release artifact;
- provider-free;
- execution-ineligible;
- provenance-bound;
- digest-verified.

A missing technical domain pack produces an unresolved dependency and a high-value clarification question rather than fabricated detail.

## Planning memory

Planning memory is supplied explicitly to the pipeline. Only approved entries whose topology matches the selected archetype are consulted. The package records the consulted memory IDs so replay can reproduce the same state.

Memory entries must contain:

- stable ID and version;
- scope;
- approval state;
- topology only;
- provenance;
- review policy;
- optional expiry;
- content fingerprint.

The pipeline neither creates nor modifies memory.

## Risk

The dynamic risk profile includes twelve dimensions:

- business;
- operational;
- planning;
- execution;
- dependency;
- constraint;
- change;
- security/compliance;
- rollback;
- evidence;
- ambiguity;
- provider-write.

Each dimension records inherent risk, residual risk, confidence, contributing nodes, and evidence. Residual risk at or above the configured high threshold requires human review and blocks projection.

## Clarification

The engine ranks one material question by expected information value. Examples:

- missing domain: which platform or domain is intended;
- unresolved owner: who is accountable for technical implementation;
- competing outcomes: which outcome takes priority;
- missing rollback: what recovery capability must exist.

Hard conflicts and high residual risk require human review rather than a speculative question.

## Reflection

The reflection gate emits structured findings only. It does not expose hidden chain-of-thought. It verifies:

- exactly one primary outcome;
- no control-plane leakage;
- delegated work withheld;
- conditional and future work withheld;
- routing metadata coherent;
- hard constraints satisfied;
- graph integrity;
- minimum coherent projection.

Any blocking failure causes a second projection pass with all current work withheld. Revision is deterministic and bounded.

## Planning styles

Supported styles are executive, strategic, project-management, engineering, operational, research, and concise. Style changes only `user_facing_summary`. It does not alter semantic fingerprints, graph identities, projection decisions, routing, risk, or authorization.

## Backward compatibility

V6.2 is additive:

- existing V1-V4 reasoning contracts remain unchanged;
- existing semantic, planning, orchestration, and reconciliation engines remain available;
- the new pipeline returns Reasoning Package V5;
- provider adapters receive no new authority;
- historical v5.2-v6.1.1 records remain immutable;
- v6.1.1 remains the immediate rollback until a separately authorized promotion changes release state.

## Failure behavior

| Failure | Result |
|---|---|
| Empty input | Reject input |
| Unresolved material dependency | Ask one clarification; no projection |
| Hard constraint conflict | Human review; no projection |
| High residual risk | Human review; no projection |
| Graph cycle or invalid reference | Contract validation failure |
| Routing contradiction | Contract validation failure |
| Reflection blocking finding | Reproject with no current work |
| Provider execution request during reasoning | Hard boundary conflict; zero writes |
| Corrupted digest | Contract validation failure |
| Missing registry data | Initialization of that registry fails closed |

## CloudVision example

Input:

`Task = arista cloud vision code upgrade automation pilot.`

Canonical result:

- model: `controlled-technology-pilot`;
- classification: `project`;
- destination: `portfolio_projects`;
- responsibility: `project_delivery`;
- workstream: `Active Projects`;
- clarification: none;
- provider writes: zero.

Projected business path:

- Launch the Arista CloudVision code-upgrade automation pilot
  1. Define and approve pilot scope and success measures.
  2. Assign the technical owner and confirm low-risk pilot targets.
  3. Approve pre-checks, change controls, evidence requirements, and rollback plan.

Everything else remains graph context or withheld management work.
