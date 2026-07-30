# Atlas ROS v8.1.0 Draft Release Manifest

Status: implementation candidate; not validated, authorized, published, or active.

## Target capability

Atlas ROS v8.1.0 introduces deterministic context-aware ambiguity resolution and clarification for attended workflows.

The candidate:

- extracts stable intent before asking for clarification;
- preserves unfamiliar terms as possible user-defined entities;
- scrutinizes short connector and relationship words;
- ranks a leading normalized interpretation and material alternatives;
- produces confirmatory, bounded-choice, or information-seeking questions;
- pauses only the affected item while allowing unrelated independent work to continue;
- binds user clarification to the exact capture, correlation identity, and analysis digest;
- records zero provider writes during analysis and resolution binding.

## Governing example

Input:

> build phase 1 or lew

Leading interpretation:

> Build Phase 1 of LEW

Clarification question:

> I understand that you want to build Phase 1, and LEW may be the application name. Did you mean: “Build Phase 1 of LEW”?

## Candidate assets

- `src/atlas_ros/contracts/operational_awareness/clarification.py`
- `src/atlas_ros/capabilities/operational_awareness/clarification.py`
- `schemas/operational-awareness/clarification-analysis.schema.json`
- `schemas/operational-awareness/clarification-resolution.schema.json`
- `docs/operations/CLARIFICATION_AND_AMBIGUITY_RESOLUTION_STANDARD.md`
- `docs/adr/ADR-0081-CONTEXT-AWARE-CLARIFICATION.md`
- `tests/unit/test_v810_context_aware_clarification.py`

## Schema and migration assessment

The initial candidate introduces package-level JSON contracts only. It does not propose or apply a production Notion schema migration. Any later evidence-persistence change must be separately assessed, additive, migration-tested, explicitly authorized, and read back before activation.

## Preserved production boundaries

- Current production authority remains unchanged.
- Required integrations remain GitHub, Notion, and Todoist.
- Google Drive remains optional and non-authoritative.
- No provider, Notion, or Todoist write is authorized by clarification analysis.
- No autonomous scheduling, messaging, email, calendar, credential, deletion, integration-scope, intent-memory, profile, or live-network capability is enabled.
- A leading interpretation remains a proposal and cannot authorize execution.
- Immutable historical releases remain unchanged.

## Required validation before exact-package authorization

- Ruff and strict MyPy.
- Full pytest and branch coverage.
- Contract and capability catalog compilation.
- Generated-schema equivalence or explicit schema validation.
- Deterministic replay for identical instructions and context.
- Governing LEW fixture and all required ambiguity categories.
- No-write and no-execution-intent assertions.
- Partial-item pause and unrelated-item continuation tests.
- Resolution idempotency and wrong-capture rejection tests.
- Build-once source and wheel creation.
- Secret and dependency audits.
- Clean source and wheel installation.
- Active-release and immediate-rollback restoration evidence.

## Authorization boundary

This draft manifest does not authorize merge, tag creation, publication, production activation, schema application, provider writes, or authority changes. Those operations require a separately validated exact package, governing decision, acceptance review, Ryan’s explicit exact-package authorization, independent publication readback, and final live authority readback.
