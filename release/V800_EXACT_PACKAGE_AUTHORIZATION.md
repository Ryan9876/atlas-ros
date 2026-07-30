# Atlas ROS v8.0.0 Exact-Package Authorization

Status: **AUTHORIZED** for the exact controlled promotion sequence recorded below.

## Authorization

Ryan explicitly authorized promotion of Atlas ROS v8.0.0 in the attended Atlas operation on July 30, 2026. This authorization is bound only to the exact retained package, evidence, migration, rollback chain, and no-rebuild sequence identified in this record.

- Governing Decision: `V4D-61` — https://app.notion.com/p/3adb8344ad2c818e8690fbad6dc4bc44
- Acceptance Review: `V4V-111` — https://app.notion.com/p/3adb8344ad2c81bcb30fcb20bf77307b
- Ryan exact-package authorization: **AUTHORIZED**
- Publication authorization: **AUTHORIZED**
- Additive migration application authorization: **AUTHORIZED AFTER PASSED INDEPENDENT PUBLICATION READBACK**
- GitHub and Notion authority activation authorization: **AUTHORIZED AFTER PASSED PUBLICATION READBACK AND MIGRATION READBACK**

## Exact validated package

- Exact package source commit: `674f0c979dec8f83a1610c7435e633e2d33e673a`
- Validated implementation merge: `b3283850c1bfb025b472f2e9e055317cc3a05f7d`
- Full validation run: `30574165764`
- Candidate artifact ID: `8772036696`
- Candidate artifact SHA-256: `9202086b86df6f727daa097d476a82099ebdbd97e8e85aa433160cb8f40464ea`
- Evidence run: `30574165698`
- Evidence artifact ID: `8771997275`
- Evidence artifact SHA-256: `e480e5f2ecda736fdabae36e71fba3a8628e1b9e7240085a24fc8a6eda999f95`
- Source distribution SHA-256: `2bfd6fda0879b9508809bdb28a41f43a664bee1098ce3325b3574223cd864047`
- Wheel SHA-256: `0a308d4b4d23a86b99fe66a1e17b89340ff5ab84091b9eca277f461d13f8f8a5`
- SBOM SHA-256: `65c8642671b1729bb775540d7bcdb5af05d14659d39169c940b8c13b5a14d9ec`
- Source manifest SHA-256: `667774768014e45fb821964d2c78f8225b34f74869e7e5cb7398b1d7bb79cc05`
- Source-tree SHA-256: `a4c0ee2e4222979cbca4939fb38a405168b531f0bd6527574fe60d70205e9d8d`
- Validation receipt SHA-256: `49bf52c882ca99cefe9b7a3fdf02c0578124c2771c1dde59aa729534e2d6f5dd`
- Migration receipt SHA-256: `a87ed0b2b13bb1ebb84ec4f390bf872c777898f9dca3e365940d5aaf6bbc304a`
- Provider dry-run receipt SHA-256: `cab1a56b57350f5ba4d5e70d31a1917b24e712a4a310097aaf638f06ae5b7212`
- Package checksum index SHA-256: `48337c17c1ea56560bd87e90479ad9a8e3e079d5ad8cd51f84303252db523b08`
- Build count: `1`

## Validation gates

- Test result: `1014 passed; 0 failed; 0 errors; 0 skipped`
- Total coverage: `86.56235017216581%`
- Ruff and strict MyPy: passed
- Architecture and development-tool boundaries: passed
- Dependency audits: PyPI and OSV passed with zero known vulnerabilities
- Secret scan: 49 changed files, zero findings
- Clean source and wheel installation: passed
- Atlas ROS v7.8.0 active restoration: passed
- Atlas ROS v7.7.0 rollback restoration: passed
- Provider dry run: zero writes
- Notion writes during validation: zero
- Todoist writes during validation: zero
- Replay/idempotency: passed
- Notion/Todoist readback and partial-failure recovery fixtures: passed
- Unresolved and ambiguous person identity planning: blocked
- Cookbook and shared fixture verification: passed

## Exact additive migration

- Migration ID: `atlas.v800.delegated-work.task-update-lifecycle-fields`
- Target data source: `collection://6d035d30-6c3b-4e69-b67d-2f0315831eb3`
- Migration digest: `d153491cf626aa6628e186faf84b9643bf9f3f491a272c18df30e5d6916de5c9`
- Fixture digest: `1f721c022fcea3d0cde0ea3d4fcd6cc522b5e2193a454953d6f968c8b8eba367`
- Projected schema digest: `69977107504bd25a6a7517faa47b093c617976cc6ed7d212277f5d30cf94b303`
- Additive fields: `10`
- Destructive operations: `0`

Only the ten validated fields may be added. No property removal, rename, rewrite, type conversion, or record mutation is authorized by the migration step.

## Exact controlled sequence

1. The immutable tag must point to the exact publication transaction commit containing the final manifest, this authorization, the publication controller, independent readback controller, and trigger.
2. Package artifacts remain bound to source commit `674f0c979dec8f83a1610c7435e633e2d33e673a` and must not be rebuilt, replaced, or modified.
3. Publish immutable tag and GitHub Release `v8.0.0`.
4. Independently verify the tag target, all published assets, exact hashes, clean source and wheel installations, and v7.8.0 restoration.
5. Apply only the validated ten-field additive Notion migration after readback passes.
6. Read back all added fields and verify the projected schema digest or exact field contract.
7. Activate GitHub and Notion authority only after successful publication and migration readback.
8. Set v8.0.0 as the sole Active release and v7.8.0 as immediate rollback.
9. Preserve v7.7.0 and older releases as historical rollback records.
10. Perform final live authority, integration, migration, rollback, provider-write, and preserved-boundary readback.
11. Confirm zero unauthorized provider writes occurred.

## Preserved boundaries

This authorization does not permit autonomous scheduling, messaging, email, calendar actions, credential actions, deletion, integration-scope expansion, Todoist task creation, profile activation, broad intent inference, or live-network execution.
