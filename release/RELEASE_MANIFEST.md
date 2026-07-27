# Atlas ROS v6.5.0 Release Manifest

Status: Active production release after exact-candidate validation, final-package Full Validation V4V-48, Ryan's explicit production authorization, governed single-controller validation, immutable GitHub publication, published-asset checksum verification, clean-install verification, rollback restoration, post-publication readback V4V-49, and live-authority activation on 2026-07-27.

- Package version: `6.5.0`
- Validated candidate head: `1412e615726e27fd1880222598c1271d4e466058`
- Candidate merge commit: `4247baf812eae3635408af2fb61761685ea1115f`
- Candidate CI run: `30265942941` — passed
- Candidate release-validation run: `30265942909` — passed
- Validated candidate artifact ID: `8654164435`
- Validated candidate artifact digest: `cc46bd3725717a620c9872ac0da81667e31298b444bab8a125ae94506c9ac040`
- Final-controller validated head: `1d80e42a3737c6c806dd53b0e50426c92d66d490`
- Final-controller validation run: `30270719879` — passed
- Final-controller validation artifact ID: `8654714988`
- Final-controller validation artifact digest: `e4ea3a4de78570972ee9440d0095d7d40438425f1add5cc7ef4108bc273c0b0b`
- Publication-controller merge commit, production source, and final tag target: `bb6d6fea70d6824c9bc6a42e63ba36cc88029260`
- Final wheel SHA-256: `dab11bd9957b175d6ac7de9058318437d6b10a8a68a477031d2e00010ecfae44`
- Final source SHA-256: `740ebe9d468030d97c47aac7009c0df4095fbec757af1d7c55ba2a42e654453d`
- Published at: `2026-07-27T13:35:16Z`
- Post-publication verification head: `bbe463b63298dc31e4f47999fdaaa7e47650cdbf`
- Post-publication verification run: `30271310940` — passed
- Post-publication verification artifact ID: `8654931210`
- Post-publication verification artifact digest: `046e142bff8d77b9c547130f83ea0202a9415c164133123442aec7fcf6485308`
- Governed reviews: `V4V-48 — Atlas ROS v6.5.0 Final Promotion Package Validation` and `V4V-49 — Atlas ROS v6.5.0 Production Publication and Readback Verification` — passed; no blocking findings
- Promotion decision: `V4D-36 — Promote exact Atlas ROS v6.5.0 release to Active production`
- Final release: https://github.com/Ryan9876/atlas-ros/releases/tag/v6.5.0
- Immediate immutable rollback: Atlas ROS v6.2.0 at production source `863d5ddf9ebd4723200166cf31c7acd93ebec54f`
- Historical rollback retained: Atlas ROS v6.1.1 at production source `e1b842765376c9e36bbdee981cddead3feb97173`
- Provider writes during validation, publication, and verification: `0`

## Authority model

GitHub is the canonical source, architecture, policy, schema, runbook, release, validation, restoration, and historical-software authority. Notion remains the live dynamic management authority. Todoist remains the attended execution authority. The fixed Google Drive Release Index remains the initialization bootstrap, while historical Drive release folders remain immutable legacy-read-only records.

Required production integrations remain Google Drive, Notion, and Todoist. Integration Inventory authority: https://app.notion.com/p/8ba4fafb5ce244ef9add3013aff3746b

## Release scope

Atlas ROS v6.5.0 adds five separated, deterministic, provider-free execution-intelligence capabilities:

1. governed framework composition with explicit precedence, provenance, policy-conflict detection, and fail-closed dependency checks;
2. minimum-effective-path planning that preserves mandatory controls, ordered prerequisites, rollback, and escalation information;
3. execution intelligence for evidence, idempotency, retry, partial failure, readback completion, and next valid actions without provider writes;
4. human-readable presentation that separates facts, assumptions, warnings, blockers, decisions, and next steps while redacting sensitive values; and
5. advisory scenario intelligence for immutable provider-neutral snapshots with explicit uncertainty, trade-offs, reversibility, and decision triggers.

The release is additive and preserves v6.2 behavior unless a caller explicitly uses the new public contracts and engines. No integration scope, Todoist behavior, scheduling, messaging, email, deletion, live network execution, autonomous action, or provider-write capability is added.

## Validation

Ruff, architecture validation, strict MyPy, dependency and secret security, 495 tests with 88.76% branch-aware coverage, execution-planning benchmark 52/52, package construction, source checksums, SBOM identity, clean v6.5.0 installation, exact candidate restoration, v6.2.0 immediate rollback restoration, v6.1.1 historical rollback restoration, six restoration authorities, all nested evidence and publication checksums, and zero-provider-write controls passed.

The immutable `v6.5.0` tag points exactly to `bb6d6fea70d6824c9bc6a42e63ba36cc88029260`. The published release is neither draft nor prerelease. All published assets were downloaded independently; `CHECKSUMS.sha256` passed; final source and wheel hashes matched `FINAL_IDENTITY.json`; the published wheel installed cleanly; v6.2.0 and v6.1.1 restored successfully; and provider writes remained zero.

## Non-blocking historical finding

The immutable v6.1.0 distribution metadata reports `6.1.0`, while its internal `atlas_ros.__version__` reports `5.0.0rc1`. The package remains installable and historical assets remain unchanged.

## Published workspace validity

The readable published workspace is valid: the active manifest, release notes, scope, final identity, validation evidence, rollback evidence, SBOM, checksums, source distribution, wheel, final GitHub Release, production source, immutable final tag, v6.2.0 immediate rollback record, and v6.1.1 historical rollback record are readable and internally consistent. Secrets and private signing material are excluded.
