# Atlas ROS v7.1.0 Final Package and Promotion Runbook

## Purpose

This runbook separates candidate compilation, final-package preparation, immutable publication, independent publication readback, and authority activation. Each stage is fail closed and requires the exact authority appropriate to that stage.

## Current authority during packaging

Atlas ROS v7.0.1 remains the sole Active production release while a v7.1.0 final package is prepared. The live `governance/AUTHORITY.json`, generated Release Index, Notion System State, and Integration Inventory must not be changed during packaging.

## Required committed release inputs

The exact source commit used for final packaging must contain:

- `release/RELEASE_MANIFEST_V710.md` — authority-neutral immutable production manifest;
- `release/RELEASE_MANIFEST_V710_CANDIDATE.md` — preserved candidate evidence;
- `release/specifications/V710.yaml` — candidate-only compiler specification;
- the version-neutral release compiler;
- the production-manifest validator; and
- the non-publishing final-package workflow.

The production manifest must never contain candidate-only or inactive-state declarations. The candidate compiler must remain candidate-only and must never publish or change authority.

## Packaging transaction

1. Resolve and verify the current live authority chain.
2. Check out the exact merged source commit.
3. Run quality, architecture, legacy-isolation, strict typing, complete tests, dependency-policy, secret, and vulnerability gates.
4. Validate the committed production manifest and preserve the candidate manifest separately.
5. Compile the candidate artifacts twice and verify deterministic equality.
6. Build the source distribution and wheel once.
7. Clean-install the wheel and verify runtime identity.
8. Generate the source manifest, SPDX SBOM, final-package identity, promotion inputs, and staged authority.
9. Restore v7.0.1, v6.5.0, and v6.2.0 from immutable assets.
10. Compare startup behavior against v7.0.1.
11. Verify all nested checksums.
12. Retain the exact package as a GitHub Actions artifact.

The final identity must remain:

- `production_authorized: false`
- `published: false`
- `authority_activated: false`

## Promotion authorization gate

A promotion request must identify the exact:

- source commit;
- retained artifact ID and artifact digest;
- source and wheel SHA-256 values;
- immutable manifest path and canonical digest;
- SBOM and source-manifest digests;
- staged authority and Release Index digests;
- tag `v7.1.0`; and
- immediate rollback v7.0.1.

Authorization for a prior commit or artifact cannot be reused.

## Publication transaction

After exact-package authorization only:

1. Revalidate the retained artifact and nested checksums.
2. Create immutable tag and GitHub Release `v7.1.0` targeting the exact authorized source commit.
3. Upload only the exact authorized package and evidence files.
4. Read back the tag, Release metadata, assets, checksums, manifest, wheel, and clean-install identity.
5. Stop without changing authority if any readback fails.

Publication alone does not make v7.1.0 Active.

## Authority activation transaction

After independent publication readback only:

1. Compile the final `AUTHORITY.json` and generated Release Index from the published identities.
2. Validate the proposed GitHub authority against the immutable published manifest.
3. Update GitHub authority through a reviewed exact-change transaction.
4. Update Notion System State to the identical release and rollback identities.
5. Reconcile Integration Inventory readiness without expanding scope.
6. Perform final live readback in authority order.

The required production integrations remain exactly GitHub, Notion, and Todoist. Google Drive remains optional, non-authoritative, and outside initialization.

## Excluded actions

This release process does not authorize Drive deletion or retirement, historical deletion, credential actions, integration-scope expansion, messaging, calendar writes, or unattended consequential execution.
