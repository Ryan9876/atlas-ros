# Atlas ROS v6.2 Operator and Recovery Runbook

## Operating state

V6.2 input processing is provider-free. Running the pipeline does not create Todoist tasks, Notion pages, calendar events, messages, network changes, provider commands, or execution receipts.

## Normal operation

1. Confirm the installed package version.
2. Load the governed archetype and domain-pack registries.
3. Submit raw input to `AdaptiveInputProcessingPipelineV62.process`.
4. Verify the final package digest.
5. Review these gates in order:
   - constraint execution eligibility;
   - material confidence floor;
   - clarification status;
   - residual risk and review requirement;
   - reflection result;
   - projection review state.
6. Display the user-facing summary and projected current business nodes.
7. Do not invoke provider application unless a separate execution plan and attended authorization exist.

## Required readback fields

- `contract_version = 5`
- `architecture_version = 6.2`
- `provider_writes = 0`
- `execution_authorized = false`
- valid nested and package digests
- coherent classification and destination
- coherent responsibility and workstream
- clarification state matching `requires_human_decision`

## Stop conditions

Stop before execution planning when:

- any material confidence dimension fails;
- ambiguity is 0.30 or higher;
- contradiction is 0.20 or higher;
- a material dependency is unresolved;
- a hard constraint conflict exists;
- residual risk is high or critical;
- clarification or human review is required;
- graph integrity fails;
- reflection blocks;
- the package digest is invalid;
- provider writes are nonzero;
- execution authorization is true inside the reasoning package.

## Clarification handling

Ask only `clarification.question`. Do not expose internal scoring traces or hidden chain-of-thought. After an answer, rerun the full pipeline with the clarified input and the same immutable registry and memory state. Do not mutate the prior package.

## Registry failure

Symptoms:

- missing JSON file;
- empty registry;
- invalid required fields;
- digest validation failure;
- unapproved registry item.

Response:

1. Stop processing.
2. Confirm the installed wheel includes both JSON registries.
3. Compare registry checksums to the candidate manifest.
4. Restore the exact candidate artifact or roll back to v6.1.1.
5. Do not create an ad hoc registry in production.

## Graph failure

Symptoms:

- duplicate node or edge ID;
- invalid node reference;
- self-cycle;
- dependency cycle;
- orphaned material node.

Response:

1. Preserve the raw input and failed package evidence.
2. Record the graph finding without projecting work.
3. Reproduce using the exact package, registry, and memory digests.
4. Correct the engine or governed registry on a feature branch.
5. Add a deterministic regression case.
6. Run Full Validation before release.

## Coherence failure

Symptoms:

- high-confidence model with unresolved responsibility;
- classification-to-destination mismatch;
- `Needs Clarification` while no human decision is required;
- explanation says clarification is required while status says no;
- projected work exists while review is required.

Response:

- reject package validation;
- do not compensate by manually altering only one metadata field;
- rerun from canonical input after correcting the source engine or evidence;
- add the contradiction to the reasoning-coherence benchmark.

## Performance degradation

If v6.2 p95 exceeds the active baseline by more than 20%:

1. retain the performance report and exact commit;
2. identify stage-level timing if available;
3. evaluate graph size, registry loading, repeated serialization, and reflection cost;
4. optimize without weakening validation or provider separation;
5. if the regression is accepted, create a Decision Log entry with evidence and alternatives;
6. do not promote without explicit acceptance.

## Candidate validation

The authoritative candidate path is `.github/workflows/release-candidate.yml`. It checks out the exact pull-request head and invokes `scripts/validate_v620_candidate.sh`, which binds the run to the candidate commit and retains checksum-verifiable evidence.

For provider-free local development validation, run:

```bash
ruff check .
python scripts/validate_architecture.py
mypy src
pytest
python scripts/evaluate_classification_intelligence.py --dataset benchmarks/classification-intelligence-v1.json --output test-results/classification-intelligence.json
python scripts/evaluate_knowledge_management.py --dataset benchmarks/knowledge-management-v2.json --output test-results/knowledge-management.json
python scripts/evaluate_semantic_fidelity.py --dataset benchmarks/semantic-fidelity-v1.json --output test-results/semantic-fidelity.json
python scripts/evaluate_reasoning_coherence.py --dataset benchmarks/reasoning-coherence-v1.json --output test-results/reasoning-coherence.json
python scripts/evaluate_execution_planning.py --dataset benchmarks/execution-planning-v1.json --output test-results/execution-planning.json
python scripts/evaluate_execution_orchestration.py --dataset benchmarks/execution-orchestration-v1.json --output test-results/execution-orchestration.json
python scripts/evaluate_canonical_reconciliation.py --dataset benchmarks/canonical-reconciliation-v1.json --output test-results/canonical-reconciliation.json
python scripts/evaluate_adaptive_input_processing.py --dataset benchmarks/adaptive-input-processing-v1.json --output test-results/adaptive-input-processing.json
python scripts/scan_candidate_secrets.py --root . --output test-results/secret-scan.json
python -m build
```

The governed GitHub Actions controller additionally:

1. generates and verifies the source checksum manifest;
2. installs the candidate wheel in a clean environment and runs the CloudVision critical case;
3. downloads and restores the active v6.1.1 baseline and preserved v6.1.0 rollback assets;
4. compares v6.2 p95 performance with v6.1.1;
5. records any preserved historical-package identity warning without modifying immutable assets;
6. generates the SBOM, candidate manifest, evidence checksums, and publication checksums;
7. uploads the exact candidate evidence artifact.

A local run that requires release-asset download must use an authenticated GitHub CLI session with read access to the repository. Do not place credentials in command history, source files, logs, or evidence artifacts.

## CloudVision acceptance check

Expected parent:

- Launch the Arista CloudVision code-upgrade automation pilot

Expected current checkpoints:

1. Define and approve pilot scope and success measures.
2. Assign the technical owner and confirm low-risk pilot targets.
3. Approve pre-checks, change controls, evidence requirements, and rollback plan.

Expected routing:

- classification: project
- destination: portfolio_projects
- responsibility: project_delivery
- workstream: Active Projects
- clarification: not required
- human review: false
- provider writes: zero

## Rollback

During candidate work, production remains unchanged. To abandon the candidate:

1. close the draft pull request;
2. retain the Decision Log and failed Review Record;
3. keep v6.1.1 active and v6.1.0 as the current immediate rollback according to live state;
4. do not alter the Release Index, System State, final tag, or GitHub Release;
5. preserve the branch and evidence if required for audit.

After a future v6.2 promotion, the exact promotion manifest must identify the immediate rollback and restoration assets. Do not infer that state from this runbook.
