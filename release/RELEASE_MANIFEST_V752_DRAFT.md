# Atlas ROS v7.5.2 Draft Immutable Release Manifest

Status: implementation candidate only; not authorized for publication or production activation.

## Scope

Atlas ROS v7.5.2 adds disabled-by-default, shadow-only clarification calibration and evaluation around the accepted v7.5/v7.5.1 behavior. The evaluator is deterministic, provider-neutral, snapshot-bound, non-authoritative, unable to route records, unable to authorize execution, and unable to create Todoist tasks or provider writes.

## Determinism

Identical snapshots, original inputs, user responses, feature flags, and evaluation-version inputs must produce an identical `ClarificationEvaluationReportV1` deterministic digest.

## Package identity

The exact source commit, retained artifact ID, artifact digest, source-distribution digest, wheel digest, SPDX SBOM digest, source-manifest digest, validation-receipt digest, and this manifest's final canonical digest remain unset until the candidate is frozen and complete non-publishing validation passes.

## Production integrations

Required integrations remain exactly GitHub, Notion, and Todoist. No integration-scope change is proposed. Google Drive remains optional and non-authoritative.

## Production schema

No production Notion schema migration is required. Evaluation persistence uses retained validation artifacts and receipts only.

## Rollback

Expected rollback at the candidate checkpoint: Atlas ROS v7.5.1, with v7.5.0 preserved as its immediate rollback. Live authority must be reread before any publication transaction.

## Preserved boundaries

No publication, tag creation, authority activation, Notion System State update, production schema write, provider migration, Todoist write, messaging, scheduling, credential action, integration-scope change, deletion, or live-network action is authorized by this draft.
