# Atlas ROS v6.5 Traceability and Definition of Done

- Status: implementation in progress
- Baseline: Atlas ROS v6.2.0 production source `863d5ddf9ebd4723200166cf31c7acd93ebec54f`
- Development branch: `agent/v650-governed-execution-intelligence`
- Immediate immutable rollback: Atlas ROS v6.1.1 at `e1b842765376c9e36bbdee981cddead3feb97173`
- Scope authority: Ryan's 2026-07-27 v6.5 Full Implementation and Production Promotion Prompt, constrained by active v6.2.0 release controls and ADR-065.

## Definition of Done

v6.5 is complete only when all requirements below are implemented, testable, backward-compatible, provider-free in the core, release validated from a clean checkout, independently reviewed as required, published from an exact validated commit, and all live authorities agree that v6.5 is the sole Active release with v6.2.0 as the immediate immutable rollback. No requirement may be marked complete based only on an ADR, schema, stub, or isolated test.

## Traceability matrix

| ID | Capability / control | Acceptance criteria | Implementation | Tests / evidence | Status |
|---|---|---|---|---|---|
| V65-FDN-01 | Shared advisory foundation | Versioned, forward-compatible schemas; provenance; assumptions; unknowns; confidence; alternatives; receipts; warnings; blockers; decisions; canonical deterministic digests; stable IDs and replay; explicit fact/inference/proposal/approval/action states | `contracts/advisory_v1.py` exists but is incomplete | Contract, serialization, property, replay, and redaction tests required | Partial |
| V65-GOF-01 | Governed framework composition | Deterministic authority precedence; governed-source versions; immutable rules vs preferences; typed serializable result; conflict, stale/missing/cyclic/incompatible input detection; no lower-authority override or provider write | Not implemented | Unit, negative, contract, and integration tests required | Not started |
| V65-MEP-01 | Minimum effective path | Minimal sufficient governed path with prerequisite, ordering, gate, evidence, rollback, risk, reversibility, cost, side effect, availability, unknown, escalation, and deterministic order semantics; mandatory controls never removed | Not implemented | Unit, property, negative, composition, and end-to-end tests required | Not started |
| V65-EIX-01 | Execution intelligence | Full governed state model, valid transitions, receipt/evidence association, idempotency, retry, partial failure, resume, read-after-write distinction, no false completion, audit replay, redacted failures, next valid action; provider-free core | Not implemented | State-transition, concurrency, retry, resume, replay, failure-path, and redaction tests required | Not started |
| V65-HRP-01 | Human-readable presentation | Executive and technical evidence-backed views; verified facts/actions/warnings/blockers/decisions/assumptions/next steps separation; stable audit references; visible partial/stale/conflicting state; Markdown/plain-text safety and secret protection | Not implemented | Golden, accessibility/structure, negative claim, and redaction tests required | Not started |
| V65-SCN-01 | Scenario intelligence | Provider-free baseline-versus-alternative analysis; explicit input and constraints; isolated/no-side-effect operation; changed assumptions and downstream effects; confidence/uncertainty; risks, tradeoffs, reversibility, failure modes, decision triggers; deterministic replay and analysis labeling | Not implemented | Scenario, comparison, determinism, isolation, and replay tests required | Not started |
| V65-INT-01 | Public interfaces | Typed APIs, schemas, exports, entry points, adapters and documentation wire all five capabilities; legacy behavior unchanged when v6.5 is unused; migration/rollback if needed | Not implemented | API, schema compatibility, regression, installation, and migration tests required | Not started |
| V65-SEC-01 | Security and privacy | Authority escalation, injection, secret exposure, unsafe deserialization, digest ambiguity, receipt tampering, side effects, supply-chain, and cyclic/malformed input risks evaluated and controlled | Not implemented | Static/dependency/secret scans and adversarial tests required | Not started |
| V65-REL-01 | Release engineering | Exact candidate artifacts, checksums, SBOM, manifest, scope, notes, migration/recovery documentation, validation evidence, PR/review, protected-branch controls, tag, release and post-promotion readback | Not started | Full clean-checkout validation and release-controller evidence required | Not started |
