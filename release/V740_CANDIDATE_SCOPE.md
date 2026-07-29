# Atlas ROS v7.4.0 Feature Delivery Acceleration Candidate Scope

Status: non-publishing development candidate only.

## Authorized scope

- Base: current `main` at development start (`8c35ad293a8c8abe729fc3b62a24dc55ec6e5fe6`).
- Reuse applicable principles from PR #63: lean/full CI separation, build-once packaging, deterministic receipts, zero-write validation, and restoration evidence.
- Add versioned feature implementation, Definition of Done, and change-impact contracts.
- Add canonical validation orchestration and development receipts.
- Add development-tooling runtime isolation checks.
- Run change-impact analysis in shadow mode only.
- Preserve complete candidate validation and manual fallback.

## Explicit exclusions

- No production promotion or Active authority change.
- No production tag or GitHub Release publication.
- No production Notion migration or System State mutation.
- No Todoist task mutation.
- No integration-scope or credential change.
- No autonomous scheduling, messaging, email, calendar, deletion, or live-network action.
- No impact-selected suppression of established validation gates.

## Candidate identity

The exact candidate commit and artifact digests remain unresolved until branch validation passes and the source is frozen. Any source change after freeze creates a new candidate identity.

## Promotion boundary

Promotion requires a separate Ryan authorization covering the exact frozen commit and exact artifact identities.
