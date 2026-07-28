# Atlas ROS v7.0.1 Corrective Release Scope

## Status

Non-publishing corrective candidate. Atlas ROS v7.0.0 remains the sole Active production release until v7.0.1 exact-package validation, authorization, immutable publication, independent readback, and canonical authority activation complete.

## Included

- Runtime and distribution identity `7.0.1`.
- GitHub-only initialization through `governance/AUTHORITY.json` and its generated GitHub Release Index.
- SHA-256 binding of the versioned immutable release manifest.
- Removal of Google Drive from startup and required production integration scope.
- Exact required production integration set: GitHub, Notion, and Todoist.
- Explicit optional/non-authoritative classification for Google Drive legacy history.
- Corrective ADR and release policy.
- Tests for Drive-required rejection, optional-Drive tolerance, generated-index integrity, immutable-manifest integrity, and patch-family authority compilation.
- Full security, package, clean-install, rollback, checksum, and non-publishing controller validation.

## Excluded

- Google Drive deletion, retirement, movement, or credential revocation.
- Pre-v6 historical cleanup.
- Any change to Todoist destinations, labels, assignment behavior, or attended execution scope.
- Autonomous scheduling, messaging, email, calendar, deletion, or live-network execution.
- Publication, tag creation, or authority activation without separate exact-package authorization.
- Modification of immutable v7.0.0, v6.5.0, or v6.2.0 release assets.

## Required before promotion

- Lean CI on the exact candidate head.
- Full CI, branch-aware tests, architecture validation, strict MyPy, secret scan, dependency policy, PyPI audit, and OSV audit.
- Build-once source distribution and wheel with exact SHA-256 identities.
- Clean installation reporting `7.0.1`.
- GitHub-only initialization acceptance tests using the candidate authority model.
- Immutable v7.0.0 and v6.5.0 restoration.
- Exact package checksums, source manifest, SBOM, and nested evidence verification.
- Review Record identifying the exact candidate commit and artifact.
- Merge of the non-publishing candidate.
- Separate Ryan authorization naming the exact source commit, artifact digest, source hash, and wheel hash.
- Governed publication controller, immutable `v7.0.1` tag and GitHub Release, and independent post-publication readback.
- Live activation of GitHub authority, Notion System State, and Integration Inventory.

## Live activation contract

After successful publication readback:

- `governance/AUTHORITY.json` identifies v7.0.1 and immutable v6.5.0 rollback.
- `governance/RELEASE_INDEX.md` is its generated projection.
- `release/RELEASE_MANIFEST_V701.md` is resolved and digest-verified at the immutable v7.0.1 commit.
- Notion System State agrees.
- Integration Inventory explicitly marks GitHub, Notion, and Todoist as required and Google Drive as optional/non-authoritative.
- Initialization reads no Google Drive content.
