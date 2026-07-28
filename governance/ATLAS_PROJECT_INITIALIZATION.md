# Atlas ROS Initialization Instruction

This is the verified external-project initialization instruction. It mirrors the live GitHub-first authority chain and contains no Google Drive bootstrap dependency.

## Quick Initialization

1. Read `governance/AUTHORITY.json` from the canonical GitHub authority ref.
2. Verify its schema and content digest.
3. Read `governance/RELEASE_INDEX.md` from the same authority ref and verify the digest declared by `AUTHORITY.json`.
4. Read the versioned immutable Active-release manifest from the exact commit named by `AUTHORITY.json` and verify its declared canonical digest.
5. Read the Notion System State URL named by `AUTHORITY.json`.
6. Read the Integration Inventory URL named by the immutable Active-release manifest.

Initialization succeeds only when the GitHub authority record, generated Release Index, immutable manifest, Notion System State, and Integration Inventory agree on exactly one Active release, one immediate rollback, release identity, required integrations, and published-workspace validity.

Required production integrations are exactly GitHub, Notion, and Todoist. Google Drive is optional, non-authoritative historical access. It is not read during initialization and is not a release, restoration, runtime, or required-integration authority.

## Consequential Work

For release, recovery, migration, audit, authority changes, integration-scope changes, or other consequential work, perform Full Validation of GitHub release assets and checksums, active and rollback restoration, current governance records, repository state, workflows, decision and review records, automation state, and Integration Inventory before writing.

## External control alignment

The active ChatGPT Atlas project instruction surface is aligned to this GitHub-first sequence. Any future external-control change must use a supported auditable platform mechanism or be performed manually by Ryan, followed by readback and a governed review record.
