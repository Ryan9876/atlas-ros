# Atlas ROS v5 Repository Audit and Master Implementation Plan

Date: 2026-07-22

Status: Evidence-based development roadmap. This document does not replace the live Release Index, active release manifest, or Notion System State.

## Executive result

The uploaded repository is the authoritative v5 working copy. Atlas ROS v4.5.3 remains the sole Active production authority and v4.5.2 remains the immediate immutable rollback. The uploaded branch contains three local governed-intelligence commits beyond its bundled remote-tracking ref plus an uncommitted decision-pipeline worktree. GitHub contains two later branch commits whose aggregate source difference is limited to Ruff-oriented formatting in `scripts/prepare_v500_promotion.py`; no unique runtime behavior was found.

The repository is substantially beyond the speculative roadmap. Memory, evidence, claim graphs, inference, reasoning, prediction, learning, evaluation, calibration, candidate preparation, validation workbench, and release control are implemented. The immediate critical scope is the governed pipeline and release-candidate evidence, not a new memory implementation.

## Authority and repository baseline

| Item | Verified state |
|---|---|
| Active production release | Atlas ROS v4.5.3 |
| Immediate rollback | Atlas ROS v4.5.2, immutable |
| Development version | 5.0.0rc1 |
| Working branch | `atlas/release-v500-candidate` |
| Uploaded HEAD | `a18d589` |
| Local divergence | Three commits beyond bundled `origin/atlas/release-v500-candidate` |
| GitHub divergence | Two later Ruff-only branch commits; no unique behavior |
| Working-copy authority | Uploaded repository, per Ryan's explicit confirmation |
| Promotion boundary | No commit, push, Candidate declaration, or production promotion without Ryan's approval |

## Complete source inventory

The executable package contains 55 Python modules, 9,465 physical lines, and 571 class/function definitions. The repository contains 36 test modules, 239 collected tests, seven schema files, and 37 documentation files.

| Area | Modules |
|---|---|
| Package and CLI | `atlas_ros.__init__`, `atlas_ros.cli` |
| Adapters | `adapters.__init__`, `errors`, `keychain`, `llm`, `notion`, `todoist` |
| Configuration and data | `config.loader`, `data.__init__` |
| Domain | `domain.__init__`, `domain.models` |
| Intelligence core | `intelligence.__init__`, `records`, `record_store`, `record_io`, `migrations`, `models` |
| Evidence and reasoning | `evidence_graph`, `claim_graph`, `inference`, `reasoning`, `decision_governance`, `decision`, `orchestration` |
| Memory and adaptation | `memory`, `prediction`, `learning` |
| Evaluation | `dataset`, `evaluation`, `evaluator`, `benchmark_adapter`, `benchmark_scoring`, `judgment_mapper`, `calibration`, `io` |
| Release intelligence | `release_readiness`, `candidate_preparation`, `validation_workbench`, `release_control_center` |
| Rules | `rules.__init__`, `rules.engine`, `rules.readiness` |
| Runtime | `runtime.__init__`, `runtime.database`, `runtime.outbox` |
| Workflows | `workflows.__init__`, `reconciliation_state`, `w01_capture`, `w02_routing`, `w03a_decomposition`, `w03_todoist`, `w04_reconciliation`, `w04_trust` |
| Release tooling | `release.tooling` |

## Architecture and dependency findings

The internal dependency graph contains 111 unique package-level import edges and now has no circular self-import. The dominant dependency direction is:

1. Canonical records and append-only persistence.
2. Evidence and claim analysis.
3. Governed inference.
4. Governed reasoning.
5. Separate policy governance.
6. Decision facade and workflow orchestration.
7. Evaluation, candidate preparation, validation, and release-control evidence.

Architectural ownership is preserved:

- `GovernedReasoningEngine` owns option scoring, evidence/claim assessment, uncertainty, and recommendation generation.
- `GovernedDecisionEngine` owns persisted policy resolution and disposition selection.
- `GovernedDecisionPipeline` coordinates reasoning followed by governance.
- `IntelligenceOrchestrator` coordinates optional inference, attaches its conclusion only to declared target options, runs the decision facade, and persists produced canonical records.
- None of these components can promote a release or change production authority.

## Public API and packaging audit

- `atlas_ros.intelligence.__all__` contains 106 unique names; every name resolves and no duplicate export exists.
- New inference request, governance engine, default policies, decision facade, and orchestration models are exported.
- Ruff and strict MyPy pass across the repository.
- The source tree builds as `atlas-ros==5.0.0rc1` for Python 3.12 or later.
- Runtime `RecordKind` values and all published record-reference JSON-schema enums are synchronized.
- The wheel intentionally packages executable code and governed YAML data; repository documentation, release evidence, and standalone JSON schemas remain source/release artifacts rather than runtime wheel resources.

## Dead-code and duplication audit

- Ruff found no unused imports, variables, or unreachable lint violations after reconciliation.
- Vulture 2.16 found no unused code at 80% or higher confidence under `src`, `scripts`, or `tools`.
- No duplicate runtime implementation requiring deletion was identified. Similar-looking components have distinct contracts: evaluation aggregates fixed metrics; calibration measures label quality; candidate preparation decides evidence completeness; the validation workbench executes gates; the release control center renders read-only state.
- Historical and versioned release reports are intentionally duplicated immutable evidence and must not be consolidated or rewritten.

## Corrected findings

| Severity | Finding | Disposition |
|---|---|---|
| Critical | `orchestration.py` imported its own undefined models, blocking test collection | Corrected with immutable `IntelligenceState` and `IntelligenceOutcome` models |
| Critical | Inference output was persisted but not consumed by reasoning | Corrected with explicit, validated inference target options and conclusion attachment |
| Critical | Orchestration did not persist recommendation, policy evaluations, or final governance | Corrected and verified by end-to-end persistence/readback test |
| High | New public inference, governance, and orchestration interfaces were not exported | Corrected; 106/106 exports resolve |
| High | Published RecordRef schema enums covered six kinds while runtime supported thirteen | Corrected and regression-tested against the runtime enum |
| High | Generated benchmark judgments could be treated as release evidence without expert acceptance | Corrected; the default calibration policy now blocks missing or rejected expert review |
| Medium | GitHub and uploaded branch histories diverge | Functionally reconciled; final history reconciliation remains a pre-commit step |

## Open technical-debt and release-evidence register

| Priority | Item | Release impact | Required disposition |
|---|---|---|---|
| P0 | Full current validation and deterministic build evidence | Blocking | Complete in this work session |
| P0 | Independent governed review of the final uncommitted diff | Blocking for Candidate proposal | Present final diff and validation evidence to Ryan before commit |
| P0 | The generated benchmark maps each intelligence domain to a fixed governed label, so its perfect accuracy is pipeline-smoke evidence rather than independent intelligence evidence | Blocking for calibration-based release eligibility | Obtain case-level expert judgments and acceptance; retain generated output only as a deterministic smoke test |
| P1 | Existing v5 milestone and promotion reports predate the decision pipeline | Stale evidence; cannot support Candidate status | Regenerate candidate evidence after source freeze |
| P1 | GitHub branch history lacks the uploaded local commits; upload lacks GitHub's final Ruff-only history | Push hazard | Reconcile intentionally during approved commit/push workflow |
| P2 | Canonical-record documentation previously described only the initial six records | Documentation drift | Correct in this candidate |
| P2 | Orchestration preserves successful inference records if a later stage fails | Acceptable append-only audit behavior, but no workflow-failure record exists | Add an explicit workflow execution/failure record in a later milestone if operational replay requires it |
| P2 | Performance evidence focuses on correctness and deterministic packaging | Non-blocking for current shadow-mode scope unless target thresholds are adopted | Retain benchmark timing in release review and define thresholds before production recommendation use |

## Evidence-based implementation roadmap

| Milestone | Status | Confidence | Remaining work | Priority |
|---|---|---:|---|---|
| M0 Repository baseline audit | Complete | High | Keep this report current through source freeze | Critical |
| M1 Candidate reconciliation | Complete in worktree | High | Approved commit/history reconciliation | Critical |
| M2 Governed intelligence pipeline | Implemented and locally validated | High | Final regression and review evidence | Critical |
| M3 Candidate hardening | Implemented; one governed evidence gate remains blocked | High | Expert benchmark review and final diff review | Critical |
| M4 v5.0 release review | Pending | High | Current reports, final diff, independent review, go/no-go | Critical |
| M5 Production promotion | Not authorized | High | Separate explicit Ryan authorization and authority transaction | Critical |
| Post-v5 knowledge/causal graph | Partial foundation | Medium | Graph persistence, temporal ontology, causal confirmation lifecycle | High |
| Post-v5 planning and cognitive-load governor | Partial foundation | Medium | Goal decomposition, constrained planning, question budget, interruption controls | High |
| Post-v5 multi-agent and intelligence lab | Framework not productionized | Medium | Sandboxed protocols, conflict resolution, supervisor, fixed evaluators | Medium |
| Post-v5 plugin, workflow, SDK, and UI expansion | Out of v5.0 release scope | High | Prioritize independently from measured user value | Medium/Low |

## Candidate exit criteria

The worktree may be recommended for commit only when all of the following are true:

- Ruff passes.
- Strict MyPy passes.
- All tests pass with at least 85% branch coverage.
- Source and wheel builds succeed.
- Source archive and wheel contents are inspected.
- Clean-wheel installation and packaged-policy smoke tests pass.
- Dependency lock, vulnerability exceptions, and current advisory checks pass or remain explicitly blocking.
- A current deterministic CycloneDX SBOM describes the locked runtime graph.
- Canonical source and artifact checksums verify deterministically.
- The full v5 evaluation/calibration and promotion-preparation evidence is current.
- The final diff receives governed review.
- No commit, push, Candidate declaration, or production promotion occurs before Ryan's approval.
