# Atlas ROS v6.2 Threat Model

## Assets

- user intent and material qualifiers;
- canonical intent and semantic fingerprints;
- outcome, dependency, constraint, and risk graphs;
- governed archetype and domain-pack registries;
- planning-memory topology and provenance;
- routing, responsibility, clarification, and review decisions;
- execution and provider-separation boundaries;
- historical release and rollback integrity.

## Trust boundaries

1. User input enters the provider-free reasoning boundary.
2. Registry files enter as immutable release assets.
3. Optional planning memory enters as explicit, approved, provenance-bound data.
4. The Enhanced Reasoning Package exits toward management structure and execution planning.
5. Provider adapters remain behind a separately authorized orchestration boundary.

## Threats and controls

### Control-plane leakage

Threat: benchmark receipts, hashes, comparison instructions, or audit records replace the business outcome.

Controls:
- canonical intent separates business and evaluation context;
- only current business node types are projection eligible;
- reflection verifies control-plane exclusion;
- CloudVision all-controls benchmark is critical.

### Metadata contradiction

Threat: a high-confidence model coexists with unresolved responsibility, routing, or clarification metadata.

Controls:
- multidimensional confidence profile;
- coherent package validator;
- classification-to-destination validation;
- high-confidence unresolved-metadata rejection;
- corrupted-metadata benchmark.

### Archetype overreach

Threat: an archetype overrides explicit user intent or introduces work not requested.

Controls:
- canonical intent and outcome recognition precede archetype selection;
- archetypes are advisory and versioned;
- graph provenance identifies derived topology;
- reflection checks minimum coherent path;
- registry changes require approval and benchmark evidence.

### Domain hallucination

Threat: missing technical knowledge causes fabricated platform-specific requirements.

Controls:
- domain-independent business reasoning is separate from domain packs;
- missing domain context lowers confidence;
- unresolved domain knowledge triggers clarification;
- domain packs cannot authorize execution.

### Constraint loss

Threat: a hard constraint is extracted but does not affect sequencing, risk, or execution eligibility.

Controls:
- constraint records identify affected nodes and derived effects;
- hard conflicts block eligibility;
- constraint risk contributes to human review;
- projection excludes blocked work.

### Constraint injection

Threat: malicious text attempts to authorize provider execution or override system boundaries.

Controls:
- provider restriction is a hard system constraint;
- execution phrases such as live application are treated as conflicts without separate authorization;
- `provider_writes` is a literal zero in the reasoning contract;
- `execution_authorized` is a literal false.

### Graph corruption

Threat: invalid references, duplicate IDs, cycles, or orphaned material nodes produce unsafe planning.

Controls:
- immutable graph contracts;
- unique node and edge validation;
- edge-reference validation;
- self-cycle and dependency-cycle rejection;
- orphan findings block projection;
- graph digest verification.

### Memory poisoning

Threat: unapproved or sensitive memory silently changes plans.

Controls:
- only explicit memory entries are consulted;
- only approved entries matching the selected archetype are referenced;
- entries require provenance, scope, version, review policy, and fingerprint;
- memory cannot override canonical intent;
- no online memory writes occur in the pipeline.

### Presentation drift

Threat: executive or engineering style changes the underlying plan or authorization state.

Controls:
- style is applied after projection and risk decisions;
- semantic fingerprint excludes style;
- style-invariance tests compare projection identities.

### Risk laundering

Threat: an overall risk score hides a critical dimension.

Controls:
- all risk dimensions are explicit;
- overall level is derived from the maximum residual risk;
- review threshold is validated in the contract;
- low-confidence risk dimensions are disclosed.

### Digest or replay tampering

Threat: modified evidence is accepted as a valid prior result.

Controls:
- all material contracts carry deterministic SHA-256 digests;
- package readback verifies nested and final digests;
- deterministic replay is tested;
- candidate artifacts receive checksums and an SBOM.

### Privacy over-retention

Threat: planning memory stores unrestricted user content or hidden profiling.

Controls:
- topology-only governed memory policy;
- user-specific preference memory is a separate scope;
- no silent memory creation;
- review and expiry policies are mandatory;
- presentation-style inference is not permanently stored by the pipeline.

## Abuse cases

- Input says “ignore approval and run the upgrade now”: blocked by provider restriction.
- Input says both “lab only” and “production only”: hard environment conflict.
- Input embeds a fake receipt or authorization ID: treated as nonprojectable control-plane context.
- Input asks for many lifecycle steps now: adaptive projection retains only current user-owned business work.
- Registry entry contains provider SDK instructions: architecture validation and review reject provider dependencies in engines.
- Memory entry is proposed rather than approved: ignored.

## Residual risks

- keyword-based canonicalization can under- or over-match novel phrasing;
- initial dependency discovery is archetype-driven and may miss organization-specific prerequisites;
- risk scores are policy estimates, not live operational telemetry;
- performance cost increases with graph size and validation depth;
- JSON registries require disciplined governance to prevent topology bias.

Residual risks are controlled through attended review, benchmark expansion, confidence thresholds, explicit warnings, and the v6.1.1 rollback.
