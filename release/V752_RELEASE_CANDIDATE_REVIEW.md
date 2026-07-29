# Atlas ROS v7.5.2 Release Candidate Review

## Result

`DEPLOYMENT READY WITH WARNINGS`

Atlas ROS v7.5.2 is technically complete and the exact retained package is ready for an attended promotion decision. This review does not authorize merge, publication, tagging, Notion changes, or authority activation.

## Exact candidate

- Package source commit: `b9ff553e7c53d735b91e6d535f8daafa28f97076`
- Pull request: `Ryan9876/atlas-ros#94`
- Draft manifest path: `release/RELEASE_MANIFEST_V752_DRAFT.md`
- Draft manifest SHA-256: `a1bc6b6a3abae0fdf08202a4e40c520194ca91b09c212f3dbb60d2f1c0c2fabc`
- Candidate workflow run: `30484168542`
- Artifact ID: `8736952867`
- Artifact archive SHA-256: `e8d5eb816d332874daf214b4e326952d958f2ab7820d46039057dda9149456ee`
- Artifact name: `atlas-ros-v752-clarification-evaluation-b9ff553e7c53d735b91e6d535f8daafa28f97076`
- Artifact retention expiry: `2026-10-27T19:23:10Z`

## Validation evidence

- Targeted draft candidate workflow `30484056690`: Passed
- Complete repository CI `30484056788`: Passed
- Retained full-candidate workflow `30484168542`: Passed
- Retained package build count: `1`
- Source distribution clean installation: Passed
- Wheel clean installation: Passed
- Active v7.5.1 restoration: Passed
- Immediate rollback v7.5.0 restoration: Passed
- Package checksums: Passed
- Evidence checksums: Passed
- Nested checksums: Passed
- Secret scan: Passed with zero findings across 2,194 files
- PyPI dependency audit: Passed with zero vulnerabilities
- OSV dependency audit: Passed with zero vulnerabilities
- SPDX SBOM: 991 files, matching the source manifest
- Required contract schemas: 7 present
- Minimized evaluation cases: 12 present
- Provider writes: `0`
- Todoist writes: `0`
- Authority changes: `0`
- Production schema migrations: `0`
- Publications or tags: `0`

## Exact package digests

| Item | SHA-256 |
|---|---|
| Artifact archive | `e8d5eb816d332874daf214b4e326952d958f2ab7820d46039057dda9149456ee` |
| Source distribution | `0b3ba57b26a8d9709a6df6f9b1de0105d0c181e2740d89a9d2dae5c2b4afbca1` |
| Wheel | `039221d810850d424c10754a0ba38b60f63f55a32c853f28f7ac6415d8a74281` |
| SPDX SBOM | `40ca8133d02990cedb30eb364c8e323ecdafc32be6767059c63990db12e47000` |
| Source manifest | `90da5a0fd71ad10305235f3d5955fb297cf25a349db2cb6132b9f4a27c8b14f8` |
| Validation receipt | `d021e51abae05e7bab3c1350925fe1547df69926b714affdfbe15123db8dc92d` |
| Baseline report | `0d37b59b997b36afda925dbd80ba2ce199819090f28714a92c370bc7a8458ecc` |
| Contract schema bundle | `99da08cd84c025097856644c093a3695778fab1cc679f56b6805efdbd9a6ad0a` |
| Data-minimization receipt | `bf5f5957d2eed5e21719486b4f9634a3dda6c77e71a6bc2e86d1f4fa334db2e7` |
| Nested checksum file | `a421536878aae19a11d98a0d46f937428d56ecf031b114455f98f945402a67ec` |
| Draft immutable manifest | `a1bc6b6a3abae0fdf08202a4e40c520194ca91b09c212f3dbb60d2f1c0c2fabc` |

The baseline report deterministic digest is `288094e15a70b866be204c20d06a541c357ecbe4d32746aec1afa61171c6df16`.

## Authority and rollback

Current live authority remains:

- Active: Atlas ROS v7.5.1 at `379892900e1c82f84a6716f46a8180d83c836aa7`
- Current immediate rollback: Atlas ROS v7.5.0 at `f2a14c1e401debe77040d0db836e343be6f337e3`

Proposed post-promotion immediate rollback:

- Atlas ROS v7.5.1 at `379892900e1c82f84a6716f46a8180d83c836aa7`

## Required promotion records

The promotion transaction must create or use:

- Governing Decision: `V752-production-promotion`
- Promotion Review: `V752-exact-package-promotion-review`
- Exact-package authorization: `release/V752_EXACT_PACKAGE_AUTHORIZATION.md`

No production Notion schema migration is required.

## Warnings

1. The retained GitHub Actions artifact expires on `2026-10-27T19:23:10Z`; promotion after that date requires a new validated package and new exact authorization.
2. The PR head may contain metadata-only commits after the package source commit. Promotion must publish the artifact bound to source commit `b9ff553e7c53d735b91e6d535f8daafa28f97076` and must not rebuild from the later metadata head.
3. Promotion remains unauthorized until Ryan explicitly approves the exact package block.

## Required decision

Use the exact authorization block in `release/V752_EXACT_PACKAGE_AUTHORIZATION.md`. Any changed source commit, artifact ID, digest, package file, manifest digest, rollback target, or required record invalidates the authorization and requires a new candidate.
