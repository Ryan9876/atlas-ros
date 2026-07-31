# Atlas ROS v8.1.0 Exact Package Authorization Record

Status: **PENDING RYAN AUTHORIZATION**

This record identifies the exact validated package that may be considered for controlled promotion. It does not grant authorization by itself.

## Exact package

- Version: `8.1.0`
- Package source commit: `8843a97e58efe46e632335df95487855b7971a75`
- Full validation workflow run: `30593561321`
- Retained candidate artifact: `8779256493`
- Candidate artifact SHA-256: `dc2f5d93f1d3aafe34d680f6c797fd190d0b2570e9e854cc2917057d0591a22a`
- Source distribution SHA-256: `f95eb2bcfc7875f6920061d9c5124c5be2cd5dc6dbbbce1cb671f5acdd1bec95`
- Wheel SHA-256: `97a3da1e1e239f5c8fd5af89b38a5c4c1005459e0fc77f830ba4915c6f81fa31`
- SPDX SBOM SHA-256: `e60407aea084ad55cd287bfbf4feb0f61ed6c80036e6b91128f33f8ae73a0d0e`
- Validation receipt SHA-256: `2ef1adc95b3d9e3ec268484fa1ab26c097d52d12f3b6061895ac3501a2f4fafc`
- Clarification evidence SHA-256: `df2558d519c4bdc1ee151c0c062b6a25768e5117df6cd1a95a4bdc2f0132a33f`
- Source-tree SHA-256: `6af181fa96e4147241d4c8527124225271f648e1e56d0dd1339a0e920b93fd18`
- Build count: `1`

## Independent verification

- Independent readback workflow run: `30593728650`
- Independent readback artifact: `8779299052`
- Independent readback artifact SHA-256: `8d990e20ca01bcc2a48a48d383cec1e41fb0aeeff155761f4f1e4ddde9601af7`
- Independent receipt SHA-256: `96fd1045d7c9ec5696214902b5b49a487a119d5f677272719af50dff74133b91`
- Package rebuilt: `false`
- Result: `passed`

## Validation summary

- Tests: `1,042 passed; 0 failed; 0 errors; 0 skipped`
- Total coverage: `86.56433978132885%`
- Statement coverage: `90.45194805194805%`
- Branch coverage: `70.04415011037527%`
- Ruff: passed
- Strict MyPy: passed
- Architecture and development-tool boundaries: passed
- Contract and capability catalogs: passed
- Canonical schema equivalence: passed
- Secret scan: 38 changed text files, zero findings
- PyPI audit: zero known vulnerabilities
- OSV audit: zero known vulnerabilities
- Clean source installation: passed
- Clean wheel installation: passed
- Active v8.0.0 restoration: passed
- Immediate rollback v7.8.0 restoration: passed
- Production schema changes: `0`
- Provider writes: `0`
- Notion writes: `0`
- Todoist writes: `0`

## Proposed complete promotion transaction

Authorization, when explicitly granted, must cover this exact sequence and no substitute package:

1. Merge the validated implementation and evidence-only commits without changing the retained package identity.
2. Add immutable no-rebuild publication controls bound to the exact retained artifact and checksums.
3. Publish immutable tag and GitHub Release `v8.1.0` from the retained source and wheel without rebuilding.
4. Independently verify the published tag target, assets, checksums, clean installations, zero-write evidence, and rollback restoration.
5. Confirm no production Notion schema migration is required.
6. Activate canonical GitHub authority with v8.1.0 Active and the then-current Active release as immediate rollback.
7. Activate matching Notion System State only after GitHub activation readback.
8. Perform final live cross-authority, integration, rollback, integrity, and preserved-boundary readback.

## Authorization exclusions

No authorization is presently granted for merge, publication, tag creation, GitHub Release creation, production authority activation, Notion System State activation, provider records, Todoist tasks, messaging, email, calendar actions, scheduling, credentials, deletion, integration-scope changes, profile activation, intent-memory inference, or live-network execution.

## Required authorization statement

Ryan must explicitly authorize this exact package, the identified rollback relationship, and the complete controlled promotion transaction. Any change to an identity, digest, artifact, source commit, migration assessment, rollback, or sequence invalidates this record and requires a new validation.
