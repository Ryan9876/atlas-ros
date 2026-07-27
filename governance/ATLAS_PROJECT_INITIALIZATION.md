# Atlas ROS v7 Initialization Instruction

This file is the exact replacement instruction for any external Atlas project configuration that cannot be updated through a verified API.

## Quick Initialization

1. Read `governance/AUTHORITY.json` from the GitHub repository.
2. Verify its schema and content digest, then read the active release manifest at the exact immutable commit or tag named in that file.
3. Read the Notion System State URL named in `AUTHORITY.json`.
4. Read the Integration Inventory URL named by the active release manifest.

Initialization succeeds only when the GitHub authority record, immutable manifest, Notion System State, and Integration Inventory agree on exactly one Active release, one immediate rollback, release identity, required integrations, and published-workspace validity.

Google Drive is not an initialization, release, restoration, runtime, or required-integration authority in v7. Do not read it during initialization.

## Consequential Work

For release, recovery, migration, audit, or other consequential work, perform Full Validation of GitHub release assets and checksums, active and rollback restoration, current governance records, current repository state, workflows, decision and review records, automation register, and integration inventory before writing.

## Current external control

The ChatGPT Atlas Project instruction surface is an external platform control. At candidate time it may still contain the prior Drive bootstrap wording. This file is the verified replacement instruction and must be copied to that control only through a supported, auditable platform API or manually by Ryan after v7 promotion approval. The v7 candidate must not claim that external control has already changed.