# Atlas ROS v8.1.0 Full Validation Plan

Status: planned; no validation result is claimed by this document.

## Scope

Validate the exact v8.1.0 context-aware clarification candidate without publishing, activating authority, applying a production schema, or writing to providers.

## Source controls

- Resolve the current Active release, immediate rollback, immutable manifest, Notion System State, and Integration Inventory from live authority.
- Bind validation to one exact candidate commit.
- Reject validation when the branch contains uncommitted or unbound changes.
- Build the candidate package once and retain the exact source and wheel artifacts.

## Static and contract validation

- Ruff.
- Strict MyPy.
- Python compilation.
- Architecture and development-tool boundary checks.
- Contract catalog compilation with exactly the registered clarification contracts.
- Capability catalog compilation with `atlas.context-aware-clarification` marked provider-free and unable to create execution intent.
- JSON Schema validation for clarification analysis and resolution contracts.
- Pydantic model-to-schema compatibility checks.

## Behavioral validation

Required governing fixture:

- Input: `build phase 1 or lew`
- Stable intent: `Build Phase 1`
- Preserved entity: `LEW`
- Ambiguous token: `or`
- Leading interpretation: `Build Phase 1 of LEW`
- Required confirmatory question: `I understand that you want to build Phase 1, and LEW may be the application name. Did you mean: “Build Phase 1 of LEW”?`
- Provider writes: zero.
- Downstream execution: blocked pending clarification.
- Unrelated independent work: eligible to continue.

Additional required fixtures:

- unfamiliar valid entity with no authoritative match;
- familiar connector word as the typo;
- two material target interpretations;
- missing ownership with stable outcome and date;
- voice-transcription homophone supported by bounded context;
- no needless interruption for a clear task;
- ambiguous action versus project;
- ambiguous delegation without identity evidence;
- conflicting dates and priorities;
- ambiguous pronoun and request-versus-note cases.

## Resolution validation

- Bind one user answer to one capture ID, correlation ID, and analysis digest.
- Preserve the original instruction unchanged.
- Record the clarification question, user answer, and normalized instruction.
- Reject answers bound to the wrong capture, correlation identity, or analysis digest.
- Reject duplicate resolution application after the item has resumed.
- Re-run classification and duplicate detection after resolution.
- Verify that clarification does not become broader execution authorization.

## Batch and interruption validation

- Process independent clear items around one ambiguous item.
- Pause only the ambiguous item.
- Surface the question at the next safe user-visible interruption.
- Do not delay the first clarification opportunity until the final batch report.
- Do not interrupt an active atomic provider transaction.
- Do not create downstream records or tasks for the ambiguous item.

## Determinism and adversarial validation

- Repeat identical instruction/context inputs and compare complete analysis digests.
- Vary irrelevant context and confirm no operational change.
- Inject prompt-like text into unfamiliar entity positions and verify it is treated as data.
- Verify unsupported alternatives are not presented to the user.
- Verify no unknown term is automatically corrected solely because it is absent from authoritative records.
- Verify the analyzer cannot call provider adapters or produce execution plans.

## Full regression

- Full pytest suite with branch coverage at or above the governed threshold.
- Existing task-update delegation, command lifecycle, idempotency, reconciliation, and initialization tests.
- Existing provider dry-run and zero-write receipts.
- Existing active-release restoration.
- Immediate-rollback restoration.
- Historical immutable-release preservation.

## Supply-chain and package validation

- Scoped secret scan.
- PyPI and OSV dependency audits.
- SPDX SBOM.
- Source manifest and source-tree digest.
- Clean source and wheel installations.
- CLI version readback as `8.1.0`.
- Nested checksum verification.

## Required retained evidence

- Exact candidate commit.
- Workflow run IDs.
- Build count.
- Source and wheel SHA-256 values.
- SBOM and source-manifest SHA-256 values.
- Test counts and coverage.
- Contract and capability catalog digests.
- Zero-provider-write receipt.
- Active and rollback restoration receipts.
- Draft final release summary.

## Stop point

Successful validation must stop at the exact-package authorization checkpoint. It must not merge, publish, tag, activate authority, apply a production migration, or perform provider writes. Those steps require a separate governing decision, acceptance review, and Ryan’s explicit authorization for the exact retained package and complete promotion sequence.
