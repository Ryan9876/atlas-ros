# Atlas ROS v6.5.0 Immutable Source Reconciliation

## Result

The immutable `v6.5.0` tag and production source remain unchanged and usable for exact package restoration. A historical metadata defect is explicitly reconciled: `pyproject.toml` at production source `bb6d6fea70d6824c9bc6a42e63ba36cc88029260` identifies package version `6.5.0`, while the in-tree `release/RELEASE_MANIFEST.md` at that same immutable source still describes v6.2.0.

## Authoritative restoration evidence

Restoration of v6.5.0 is bound to the independently verified published GitHub release assets and checksums:

- immutable tag: `v6.5.0`;
- production source commit: `bb6d6fea70d6824c9bc6a42e63ba36cc88029260`;
- final source SHA-256: `740ebe9d468030d97c47aac7009c0df4095fbec757af1d7c55ba2a42e654453d`;
- final wheel SHA-256: `dab11bd9957b175d6ac7de9058318437d6b10a8a68a477031d2e00010ecfae44`;
- current active-manifest blob: `b9eb2b180d1b2d3678d84e3c3062ffc22c7c2477`;
- stale immutable-source manifest blob: `afba3c620ccc6e074fb44a89bcab720988228b3c`.

The published v6.5.0 source distribution and wheel, `FINAL_IDENTITY.json`, and `CHECKSUMS.sha256` are the package-restoration authority. The current v6.5.0 active manifest is the release-metadata authority. The stale manifest embedded in the immutable publication-controller commit is retained only as historical repository content and must not override the verified package identity.

## Required handling

- Do not rewrite, move, or recreate the immutable `v6.5.0` tag.
- Do not amend or force-update production commit `bb6d6fea70d6824c9bc6a42e63ba36cc88029260`.
- Validate restoration against the published source and wheel hashes above.
- Confirm the restored package reports `atlas_ros.__version__ == "6.5.0"`.
- Retain v6.2.0 at `863d5ddf9ebd4723200166cf31c7acd93ebec54f` as the immediate immutable rollback.
- Treat any attempt to use the stale in-tree v6.2.0 manifest as the v6.5.0 package identity as a fail-closed reconciliation error.

## Machine-readable record

The checksum-bound reconciliation record is `release/V650_IMMUTABLE_SOURCE_RECONCILIATION.json`. Its validator is `tools/release/rollback_reconciliation.py`, and regression coverage is maintained in `tests/unit/test_v650_rollback_reconciliation.py`.

This correction changes no production authority, provider permissions, integration scope, tag, release asset, rollback target, or live system state. Provider writes performed: `0`.
