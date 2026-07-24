# Release Surface Synchronization Runbook

## Purpose

Keep the live Notion current-authority surfaces aligned with the sole Active Atlas ROS release. This workflow replaces manual version-string edits with one attended, fail-closed synchronization operation.

The synchronizer updates only these dynamic surfaces:

- Leadership Operating System production callout
- Control Center production callout
- Production workspace release callout
- Releases page Active package references and Immediate Rollback callout

Historical release pages, archived records, decision evidence, and independently versioned workflow drivers such as W03 and W04 are intentionally excluded.

## Authority and autonomy

- Google Drive Release Index and the Active release manifest remain release authority.
- Notion System State remains dynamic-state authority.
- The synchronization workflow is an **A3 consequential, attended promotion step** because it writes current production authority references.
- It never runs on a timer or merely because a candidate branch changes.
- A production environment approval and an explicit authorization reference are required before apply mode.
- Dry-run is the default.

## Promotion sequence

1. Publish and read back the immutable release package and manifest.
2. Update and read back the Google Drive Release Index and Notion System State.
3. Invoke `sync-notion-release-surfaces` with the exact Active release payload.
4. Review the dry-run evidence. Every configured surface must have the expected unique match count and no conflicts.
5. Approve the protected production environment and run apply mode.
6. The command updates each block and immediately reads it back. Any mismatch fails the operation and attempts to restore earlier writes.
7. Attach the workflow evidence to the governed Review Record. READY may be reported only after this evidence agrees with the Release Index, System State, manifest, and Integration Inventory.

## CLI

Dry-run:

```bash
python scripts/sync_notion_release_surfaces.py \
  --active-release v5.2.0 \
  --package-version 5.2.0 \
  --rollback-release v5.1.1 \
  --active-package-url https://drive.google.com/drive/folders/EXAMPLE \
  --review-date 2026-07-24
```

Apply after explicit promotion authorization:

```bash
python scripts/sync_notion_release_surfaces.py \
  --active-release v5.2.0 \
  --package-version 5.2.0 \
  --rollback-release v5.1.1 \
  --active-package-url https://drive.google.com/drive/folders/EXAMPLE \
  --review-date 2026-07-24 \
  --authorization-ref https://app.notion.com/p/RELEASE_DECISION \
  --apply
```

Configure `ATLAS_NOTION_TOKEN` in the attended process environment or the protected GitHub production environment.

## Fail-closed controls

The operation stops without writing when:

- a configured current-authority block is missing;
- more blocks match than expected;
- a matched block has an unsupported type;
- a page hierarchy contains a repeated/cyclic block reference;
- apply mode lacks explicit confirmation or an authorization reference;
- any post-write readback differs in text or link target.

If a write or verification fails after earlier blocks were updated, the synchronizer attempts to restore those blocks from the pre-write content and reports any rollback failure explicitly.

## Configuration changes

The stable current-authority page IDs are code-controlled in `atlas_ros.release.surface_sync`. Adding, removing, or structurally redesigning a current-authority surface requires tests and governed release review. Do not broaden matching rules to historical or driver-version records.
