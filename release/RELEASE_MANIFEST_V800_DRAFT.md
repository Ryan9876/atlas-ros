# Atlas ROS v8.0.0 Draft Release Manifest

Status: candidate implementation manifest only. Publication and production activation are not authorized.

## Intended identity

- Release: Atlas ROS v8.0.0
- Package version: `8.0.0`
- Intended tag: `v8.0.0`
- Exact source commit: **PENDING FULL VALIDATION**
- Source distribution SHA-256: **PENDING BUILD-ONCE ARTIFACT**
- Wheel SHA-256: **PENDING BUILD-ONCE ARTIFACT**
- SPDX SBOM SHA-256: **PENDING EVIDENCE COMPLETION**
- Source manifest SHA-256: **PENDING EVIDENCE COMPLETION**
- Validation receipt SHA-256: **PENDING FULL VALIDATION**
- Test and coverage results: **PENDING FULL VALIDATION**
- Governing Decision: **PENDING**
- Acceptance Review: **PENDING**

## Release scope

Add deterministic task-update lifecycle normalization that recognizes qualified natural-language delegation, waiting-on, blocked, complete, update, or no actionable transition. Qualified delegation is normalized into the existing typed `delegate` lifecycle and reuses current planning, Notion Delegated Work, Ryan-owned Todoist checkpoint, idempotency, authorization, execution, readback, and reconciliation architecture.

Delegate delivery due date and Ryan follow-up checkpoint remain separate. Material ambiguity fails closed before provider planning. Explicit `@atlas delegate` commands remain compatible.

## Additive migration

`release/v800-notion-schema-migration.yaml` is candidate-unapplied. No schema or record write is authorized before exact-package activation.

## Required production integrations

Exactly GitHub, Notion, and Todoist. No integration-scope change is included. Google Drive remains optional and non-authoritative.

## Rollback

The intended immediate rollback is the live Active Atlas ROS v7.8.0 immutable release resolved from authority during validation and activation. The v7.8.0 package must be restored successfully before exact-package authorization.

## Preserved boundaries

No autonomous scheduling, unattended provider write, messaging, email, calendar, credential, deletion, profile activation, broad intent inference, or live-network execution is authorized. Interpretation and planning remain non-authorizing. Adapters cannot create execution intent.

## Required controlled sequence

1. Implement on `agent/v8.0.0-task-update-delegation`.
2. Complete non-publishing validation.
3. Build exact package once and bind checksums.
4. Verify v7.8.0 restoration.
5. Record the governing Decision and Acceptance Review.
6. Obtain exact-package authorization.
7. Publish immutable tag and GitHub Release `v8.0.0` without rebuilding.
8. Independently verify publication and rollback.
9. Apply the additive migration only within the authorized activation transaction.
10. Activate GitHub and Notion authority only after verification.
11. Perform final authority, integration, provider-write, and preserved-boundary readback.

Publication alone does not activate production authority.
