# Canonical Intelligence Records — Milestone 3

## Purpose

The Canonical Intelligence Records (CIR) layer is the governed substrate for Atlas ROS v5 memory, prediction, recommendations, decisions, and outcome learning. It prevents intelligence components from exchanging undocumented dictionaries or mutating hidden state.

## Guarantees

Every record is:

- immutable after construction;
- typed and schema-versioned;
- deterministically serialized;
- content-integrity protected with SHA-256;
- traceable through provenance and typed record references;
- compatible with append-only persistence;
- rejected when references, lifecycle rules, or confidence contracts are invalid.

The integrity hash covers the complete canonical payload except the hash field itself. Record identifiers remain stable across serialization; identical payloads with identical identifiers and timestamps produce identical hashes.

## Record types

### EvidenceEnvelope

Separates an observation from later inference. It records authority level, confidence, validation status, source locator, source-content hash, observation time, citation, and provenance hops.

### ContextSnapshot

Captures the objective, constraints, user and environmental state, available authorities, decision horizon, session lineage, and evidence used at a specific point in time.

### PredictionRecord

Records a falsifiable prediction with probability, confidence interval, assumptions, expiration, evidence, and—only when both are available—actual outcome and calibration error.

### RecommendationRecord

Records the proposed action, alternatives, rationale, expected benefit and risk, confidence, context, and evidence. Recommendations cannot exist without evidence and a context snapshot.

### DecisionRecord

Records the decision owner, selected option, expected outcome, success metrics, evidence, and optional recommendation that informed the decision.

### LearningEvent

Records the observed outcome, prediction and/or decision linkage, delta analysis, confidence change, eligible pattern updates, model version, and explicit learning eligibility. Ineligible events cannot modify learned patterns.

## Persistence contract

`SQLiteIntelligenceRecordStore` provides an append-only local reference implementation:

- duplicate writes of the same immutable record are idempotent;
- writes that reuse an identifier with different content are rejected;
- stored records are revalidated and rehashed on read;
- typed references must resolve to the expected identifier, kind, and integrity hash;
- a staged record graph can be atomically validated before append.

This implementation does not activate a production data store or alter Notion, Google Drive, or Todoist authority.

## Versioning and migration

Schema versions use semantic version strings. `RecordMigrator` requires explicit source-to-target migration registration. Migrations operate on copies, update the schema version, and remove the old integrity hash so the migrated record must be validated and rehashed. No implicit or best-effort migration is allowed.

## Trust boundaries

- Observations belong in EvidenceEnvelope records.
- Inferences belong in prediction, recommendation, decision, or learning records.
- Confidence is explicit and bounded.
- Provenance is append-only evidence, not an editable narrative.
- Cross-record links are typed and hash-bound.
- Supersession creates a new record; it never changes the old record.
