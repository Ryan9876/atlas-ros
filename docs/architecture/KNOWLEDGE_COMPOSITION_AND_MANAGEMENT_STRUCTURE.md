# Knowledge Composition and Management Structure

Status: Atlas ROS v5.4.0 release-candidate architecture.

The Phase 2 pipeline is deliberately non-executing:

`Reasoning Package V3 -> Planning Model Registry -> Dependency Resolver -> Knowledge Package V2 -> Management Package V2`

Planning models are versioned declarative artifact definitions. Knowledge modules are versioned,
composable facts, section contributions, context requirements, governance overlays, and evidence
overlays. Registries resolve semantic-version constraints deterministically and expose
checksum-stable manifests. The dependency resolver expands required and explicitly selected
optional dependencies, detects cycles, incompatible constraints, conflicts, duplicate providers,
and deprecated modules, then emits a stable graph, order, trace, and digest.

Composition never calls a provider adapter and never creates execution steps. It binds known
context, applies declared precedence and merge policy, retains per-value provenance, exposes
missing context and unresolved questions, and signs the validated package payload. Structure
construction is generic: it reads the selected model's section definitions, validates dependencies
and completeness, preserves section provenance, carries governance and evidence requirements, and
stops at `decision_required` when mandatory information is absent.

The production-compatible V1 methods remain available. V2-to-V1 projection is allowed only when
it is loss-safe; unresolved or conflict-resolved packages fail closed. Configuration exists in
authoring and packaged locations, and CI verifies byte-level checksum equivalence.

## Team Operating Model

The first complete model contains Purpose, Mission, Scope and boundaries, Customers and
stakeholders, Services and outcomes, Responsibilities, Roles and accountabilities, Decision
rights, Ways of working, Meeting and communication cadence, Governance and escalation, Metrics
and service health, Continuous improvement, and Review and change control. Risk and stakeholder
communication modules are optional and must be explicitly selected.

## Security and observability

No secrets, raw content, or provider tokens are emitted. Events contain correlation, model
identity, lifecycle status, registry digest, and package digest only. Configuration is data, never
executable code. Unknown, retired, ambiguous, cyclic, or incompatible definitions fail closed.
