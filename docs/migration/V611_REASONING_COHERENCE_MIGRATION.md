# Atlas ROS v6.1.1 Reasoning Coherence Migration

## Compatibility status

Atlas ROS v6.1.1 is a compatible patch over v6.1.0. Existing Reasoning Package V4 and Management Package V3 consumers remain valid because the new fields are optional supplements with safe defaults.

## New fields

Reasoning Package V4 may include:

- `confidence_dimensions`
- `coherence_result`
- `user_facing_summary`

Management Package V3 may include:

- `confidence_dimensions`
- `reasoning_coherence`
- `user_facing_summary`

Existing legacy confidence, classification, responsibility, workstream, destination, and review fields retain their meanings. v6.1.1 populates them consistently with the new coherence evidence.

## Behavioral change

Material contradictions now fail closed before management approval and orchestration. High-confidence controlled technology pilots use governed model evidence to resolve project-delivery responsibility and the Active Projects workstream without vendor-specific rules.

## Provider boundary

The migration performs no provider writes. Todoist and Notion adapters, permissions, object budgets, authorization, idempotency, readback, reconciliation, and rollback behavior are unchanged.

## Rollback

Atlas ROS v6.1.0 remains the immutable rollback during candidate validation and after any separately authorized v6.1.1 promotion. Records created under v6.1.1 remain readable by v6.1.0 because new coherence fields are supplemental evidence and do not alter provider object semantics.
