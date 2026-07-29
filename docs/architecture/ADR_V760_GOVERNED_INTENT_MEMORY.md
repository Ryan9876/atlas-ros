# ADR — Atlas ROS v7.6.0 Governed Intent Memory

## Status

Accepted for candidate implementation; production deployment is not authorized.

## Context

v7.5.1 introduced adaptive clarification and evidence-aware familiarity. v7.5.2 added deterministic shadow evaluation. Neither release owns a durable, inspectable, correctable, context-isolated production intent-memory subsystem. Reusing Universal Inbox as the complete learning store would mix operational routing state with historical evidence and user-control records.

## Decision

Implement one governed subsystem with separate contracts and persistence targets for evidence, active indexes, and user-control receipts. Evidence is eligible only when it is attributable, confirmed, current, context-matched, active, sufficiently confident, and not contradicted. Current instructions and live authority bypass and override memory.

Context matching is fail-closed. An evidence scope may constrain user, domain, project, responsibility, request type, and sensitivity domain. A missing or different constrained dimension prevents transfer. General familiarity with Ryan does not imply familiarity with a new term, vendor, project, responsibility, request type, or sensitive context.

Corrections create a successor evidence record and mark the original corrected and ineligible. Retirement preserves the record but removes it from active indexes. Forgetting is represented as a separate governed workflow: a request removes evidence from active inference immediately, but deletion is not claimed until exact authorization, provider mutation, and live readback exist. Only a content-free tombstone may remain.

## Consequences

- Universal Inbox remains operational state.
- Three additive Notion data sources are proposed.
- The software can ship disabled before schema application.
- Inspection can be enabled separately from inference.
- Initial migration can legitimately produce zero records.
- Rollback is non-destructive: restore v7.5.2 behavior and leave additive stores unused.
