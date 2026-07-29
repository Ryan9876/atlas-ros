# Atlas ROS v7.5.2 Draft Immutable Release Manifest

## Status

- Release: Atlas ROS v7.5.2
- Manifest status: Draft candidate; not authoritative and not Active
- Promotion status: Awaiting exact-package authorization
- Source commit: `b9ff553e7c53d735b91e6d535f8daafa28f97076`
- Pull request: `Ryan9876/atlas-ros#94`
- Candidate workflow run: `30484168542`
- Candidate workflow conclusion: Success

This manifest identifies the exact validated package proposed for promotion. It does not authorize merge, publication, tagging, Notion updates, or authority activation.

## Retained candidate artifact

- GitHub Actions artifact ID: `8736952867`
- Artifact name: `atlas-ros-v752-clarification-evaluation-b9ff553e7c53d735b91e6d535f8daafa28f97076`
- Artifact archive SHA-256: `e8d5eb816d332874daf214b4e326952d958f2ab7820d46039057dda9149456ee`
- Artifact size: `1555674` bytes
- Created: `2026-07-29T19:24:56Z`
- Retention expiry: `2026-10-27T19:23:10Z`
- Expired at validation: No
- Retained build count: `1`

The downloaded archive digest was independently recalculated and matched the GitHub artifact digest.

## Exact package files

| File | SHA-256 |
|---|---|
| `atlas_ros-7.5.2.tar.gz` | `0b3ba57b26a8d9709a6df6f9b1de0105d0c181e2740d89a9d2dae5c2b4afbca1` |
| `atlas_ros-7.5.2-py3-none-any.whl` | `039221d810850d424c10754a0ba38b60f63f55a32c853f28f7ac6415d8a74281` |

Both packages passed clean installation and reported Atlas ROS version `7.5.2`. The candidate runtime reports Atlas ROS v7.5.1 as the unchanged Active production release.

## Required evidence

| Evidence | SHA-256 |
|---|---|
| SPDX SBOM, `SBOM.spdx.json` | `40ca8133d02990cedb30eb364c8e323ecdafc32be6767059c63990db12e47000` |
| Source manifest, `SOURCE_MANIFEST.sha256` | `90da5a0fd71ad10305235f3d5955fb297cf25a349db2cb6132b9f4a27c8b14f8` |
| Validation receipt | `d021e51abae05e7bab3c1350925fe1547df69926b714affdfbe15123db8dc92d` |
| Package index | `96aea95c84318736f8a4ee5b34c61e6e3ff8ab47236e8566ee346af987473807` |
| Baseline evaluation report | `0d37b59b997b36afda925dbd80ba2ce199819090f28714a92c370bc7a8458ecc` |
| Contract schema bundle | `99da08cd84c025097856644c093a3695778fab1cc679f56b6805efdbd9a6ad0a` |
| Data-minimization receipt | `bf5f5957d2eed5e21719486b4f9634a3dda6c77e71a6bc2e86d1f4fa334db2e7` |
| Secret-scan receipt | `4aeade34db497a9bb4dfb2598b63b9dd34b3476e5e1c00faf130562b3fe28d2b` |
| PyPI dependency audit | `2ff3a6ea50a3b6be4c3aebae95d16132d7f9aac973300eca6879683201f0dda6` |
| OSV dependency audit | `2ff3a6ea50a3b6be4c3aebae95d16132d7f9aac973300eca6879683201f0dda6` |
| Zero-provider-write receipt | `ed02bf7acb1adc5017afa9b75d929006c5ab783f6ced76b74e0506840ee0ea63` |
| Non-publishing controller receipt | `9559d85f3e9402d1d142e1ae1b1dad2b4a395244460292946c006485961b5ea4` |
| Definition-of-Done receipt | `cbcda56563d1bece432b2c07ca70a4d68f2920ff60b1409f1c8d8acc2861dce7` |
| Actions-utilization receipt | `b505dfa2d3b3e6b94f991c11ba2a518fb941b1dbfca1c16445cece3ba77b4f88` |
| Package checksum file | `ca7ccfb6ac8cc4ac8580369dabccbf22b009f1ba037bc37d66406e6c176cd911` |
| Evidence checksum file | `2d12b4d1f220a5eb7a8a5627e9927078fb22d5935b4d4744e615bfd062da2548` |
| Nested checksum file | `a421536878aae19a11d98a0d46f937428d56ecf031b114455f98f945402a67ec` |

The baseline report deterministic digest is `288094e15a70b866be204c20d06a541c357ecbe4d32746aec1afa61171c6df16`.

## Validation summary

- Complete repository correctness gates: Passed
- Ruff: Passed
- Strict MyPy: Passed
- Architecture boundaries: Passed
- Deterministic dependency policy: Passed
- Full pytest and coverage gates: Passed
- Execution-planning and task-economy checks: Passed
- Deterministic 12-case baseline: Passed
- Seven required contract schemas: Present
- Data minimization and fixture attribution: Passed
- Secret scan: Passed; zero findings across 2,194 files
- PyPI dependency audit: Passed; zero vulnerabilities
- OSV dependency audit: Passed; zero vulnerabilities
- Source distribution clean install: Passed
- Wheel clean install: Passed
- Package and evidence checksum verification: Passed
- Nested checksum verification: Passed
- Provider writes: `0`
- Todoist writes: `0`
- Production schema migrations: `0`
- Authority changes: `0`
- Publications or production tags: `0`

## Evaluation boundaries

- Feature mode remains disabled by default and shadow-only when enabled.
- Accepted v7.5 predecessor decisions remain authoritative.
- Counterfactual decisions are non-authoritative, cannot route, and cannot authorize execution.
- Evaluation cannot create work, suppress work, mutate provider records, or perform Todoist writes.
- No production Notion schema migration is required.
- Identical snapshots, user responses, feature flags, and evaluation-version inputs produce the same evaluation-report digest.

## Current authority and rollback

- Current Active release: Atlas ROS v7.5.1
- Current Active immutable commit: `379892900e1c82f84a6716f46a8180d83c836aa7`
- Immediate rollback release: Atlas ROS v7.5.0
- Immediate rollback immutable commit: `f2a14c1e401debe77040d0db836e343be6f337e3`
- Active restoration validation: Passed
- Immediate rollback restoration validation: Passed

If v7.5.2 is promoted, the proposed immediate rollback remains the currently published and verified Atlas ROS v7.5.1 package unless the governing promotion decision specifies otherwise.

## Required integrations

Required integrations remain exactly:

1. GitHub
2. Notion
3. Todoist

Integration Inventory:

- Notion page: `https://app.notion.com/p/8ba4fafb5ce244ef9add3013aff3746b`
- Notion data source: `collection://46af021f-eb9a-4eba-b10c-4523e70df0c3`

At candidate validation, all three required integrations were connected, approved, accepted, production-current, and least-privilege verified. Google Drive was not required or read.

## Promotion records to create or use

Promotion requires an attended transaction authorized for this exact package and recorded through:

- Governing Decision record to create: `V752-production-promotion`
- Promotion Review record to create: `V752-exact-package-promotion-review`
- GitHub candidate review: `release/V752_RELEASE_CANDIDATE_REVIEW.md`
- Exact-package authorization block: `release/V752_EXACT_PACKAGE_AUTHORIZATION.md`

No Decision or Review record is created by this draft manifest.

## Authorized promotion sequence after exact-package approval

1. Re-read live authority and confirm v7.5.1 remains Active and v7.5.0 remains immediate rollback.
2. Verify the retained artifact ID and archive digest against this manifest.
3. Create the governing Decision and Promotion Review records.
4. Merge only the reviewed PR with the expected head and package-source binding.
5. Publish the exact retained source distribution, wheel, SBOM, manifests, receipts, and checksums without rebuilding.
6. Verify the published release and immutable tag independently.
7. Update GitHub authority and generated Release Index only after publication verification.
8. Update Notion System State only after GitHub authority verification.
9. Perform final live readback across GitHub authority, Release Index, immutable manifest, Notion System State, and Integration Inventory.

Publication, merge, tagging, and authority activation remain prohibited until Ryan explicitly authorizes this exact package.
