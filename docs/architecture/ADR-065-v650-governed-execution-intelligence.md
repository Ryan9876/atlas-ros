# ADR-065: v6.5 governed execution intelligence boundaries

- Status: Accepted for v6.5 candidate implementation
- Date: 2026-07-27
- Baseline: Atlas ROS v6.2.0 production source `863d5ddf9ebd4723200166cf31c7acd93ebec54f`
- Immediate rollback: Atlas ROS v6.1.1

## Decision

Atlas ROS v6.5 will add five separate, provider-free capabilities:

1. Governed Operating Framework Composition
2. Minimum Effective Path Planning
3. Execution Intelligence
4. Human-Readable Execution Presentation
5. Scenario Intelligence

They share typed evidence, provenance, assumption, uncertainty, confidence, and advisory-receipt semantics. They do not share execution or provider authority.

## Boundaries

| Capability | Owns | Must not own |
| --- | --- | --- |
| Framework Composition | applicability, precedence, typed policy contributions | tasks, authorization, providers |
| Minimum Effective Path | canonical route through qualified work | authorization, provider commands |
| Execution Intelligence | advisory friction, activation, context fit, progress | canonical replanning, provider writes |
| Presentation | readable representation and semantic traceability | task existence, scope changes |
| Scenario Intelligence | read-only snapshot analysis and counterfactuals | plans, tasks, authorization, execution |

Existing Capture, Management Reasoning, Knowledge Composition, Management Structure, Record Routing, Execution Planner, Execution Orchestrator, Todoist Adapter, Notion Adapter, and Reconciliation responsibilities remain unchanged.

## Authority controls

- EIX must encode false for create, update, delete, schedule, send-message, authorize, execute, and online-training authority.
- Scenario Intelligence receives immutable provider-neutral snapshots and remains disconnected from live authoritative state by default.
- Presentation is digest-bound alongside the canonical execution plan at attended authorization.
- Orchestration transmits only the authorized presentation; adapters only perform provider formatting, operations, and readback.
- Reconciliation verifies displayed content against the authorized presentation and completion against canonical criteria.
- Framework packs are advisory unless an organization policy pack has authoritative source, owner, effective date, review policy, scope, and provenance.
- Generic frameworks must never claim organization adoption.

## Compatibility

Contract evolution is additive. Existing readers remain supported. Any lossy projection that would remove framework requirements, path semantics, canonical-criteria mappings, material assumptions, or presentation authorization must fail closed.

## Consequences

Implementation must add architecture validation and side-effect tests for these boundaries. No production release, tag, GitHub Release, Release Index, System State, Integration Inventory, Todoist record, or Notion management-record change is authorized by this ADR.
