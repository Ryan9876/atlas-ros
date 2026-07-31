# Atlas ROS v8.2.1 Immutable Release Manifest

Status: exact package authorized for immutable no-rebuild publication, independent verification, and controlled production activation.

## Exact package identity

- Release version: `8.2.1`
- Exact package source commit: `5a71c043292faab39df084e9eeeb0d10634d2627`
- Validated implementation merge: `ef6820dce64919248019c6f3ce23dcea2b0f2cd9`
- Full validation run: `30649452649`
- Retained candidate artifact: `8800800923`
- Candidate artifact SHA-256: `979f030eaecbc5961bd2c8701a87ce8e752908d87312127b8314fb3a85890843`
- Source distribution SHA-256: `2ebddbfacf772f40f5bf3514d3f09a691259304775bafe497685a652675961da`
- Wheel SHA-256: `fe9db86412a88acaf2f9860c5ab4a044f296880e19f787ece601a92bd5f282f0`
- SPDX SBOM SHA-256: `f0560023159d28799b897e9fbcd1196edaac3411fd50e47b01acbac565d0a458`
- Validation receipt SHA-256: `8214da5cde9b50e76cac96551764da510ffa37e56a9f2660707c36fd6fc9dc00`
- Package index SHA-256: `8d150bc3331fd071f444991e65119004c7e7e201d764f3ce55af3b1a15fbd8b2`
- Source-tree SHA-256: `df700f8fbb8d7dbe6e993d0b55d4bf507bb9818d0f082e16ada284baac25abac`
- Package checksum index SHA-256: `f5fcf005a2cb0fc14191cec569326c80daa0834df81d38a115af6f3ac9079d01`
- Evidence checksum index SHA-256: `7b783de7cac6043997cddf34cb23bed2617a19db05df35ab0f551b4f21fd4249`
- Ledger/baseline readback SHA-256: `0848a17317a7830eaea41ae5a565c9c3e2300e57d01c5b43f250d1fe7efc6ef1`
- Exact authorization SHA-256: `f3c7fc86b8b91a7cbd7d94418f29039fc0d659a6cd9ba08a2e079def27cba3c0`
- Build count: `1`
- Test result: `1,074 passed; 0 failed; 0 errors; 0 skipped`
- Total coverage: `86.3676201099514%`
- Governing Decision: `V4D-64`
- Acceptance Review: `V4V-121`

The immutable `v8.2.1` tag must point to the publication transaction commit containing this manifest, the authorization record, production ledger/baseline readback, publication controller, independent readback workflow, and publication trigger. Package assets remain bound to the exact package source commit above and must not be rebuilt.

Integration Inventory authority: https://app.notion.com/p/8ba4fafb5ce244ef9add3013aff3746b
Integration Inventory data source: `collection://46af021f-eb9a-4eba-b10c-4523e70df0c3`

## Release scope

v8.2.1 replaces the deleted historical W04 reconciliation target with one independent production `Execution Reconciliation State` ledger. It rejects both W04 identities, fails closed on missing or invalid configuration, requires a complete verified baseline checkpoint, supports connector-safe evidence encoding, preserves the exact baseline cutover despite provider date rounding, and keeps reconciliation attended and replay-safe.

## Production ledger and baseline

- Database: `e72c11168cb54d7e8069c7ac9ecb807b`
- Data source: `dc486c5d-c5d2-4386-8a50-d18d1dfb7223`
- Checkpoint: `3aeb8344ad2c8180bdb0c7c8db42b21f`
- Baseline run: `v821-production-baseline-2026-07-31T1641460000`
- Cutover: `2026-07-31T16:41:46+00:00`
- Inventory digest: `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945`
- Plan digest: `fe89bc0d454b33bb9eb135baa027b1db493f70a0a992911359964d474fe3cbab`
- Eligible mapped parents/subtasks: `31` / `89`
- Pre-cutover events written: `0`
- Replay writes: `0`
- Checkpoint readback: verified

The historical W04 database `ba2518b1-3c97-4a94-8324-414f74ed8830` and data source `afbb753c-3112-4784-9165-f786b503d1f7` remain deleted, prohibited, unrestored, and unwritten.

## Production integrations

Required production integrations remain exactly **GitHub, Notion, and Todoist**. Each must remain connected, approved, accepted, production-current, and least-privilege verified. Google Drive remains optional and non-authoritative and is not part of this promotion transaction.

## Validation and restoration

The exact package passed Ruff, strict MyPy, architecture and development-boundary checks, 1,074 tests, 86.3676% coverage, scoped secret scanning with zero findings, PyPI and OSV dependency audits, build-once source and wheel generation, clean source and wheel installation, Active v8.2.0 restoration, and immediate rollback v8.1.0 restoration. Validation performed zero production provider writes and did not restore or write W04.

## Rollback chain after activation

- Immediate rollback: Atlas ROS v8.2.0 at `64c38eb4e83f6edf2d6cff28f7c7556a2c84c0c9`
- Historical rollback: Atlas ROS v8.1.0 at `a46619c4b806a63ea1426f06171b53ee219d9d77`
- Existing older immutable rollback records remain preserved unchanged.

## Governing authorization

- Decision: https://app.notion.com/p/3aeb8344ad2c81f5a3aed1d13da466bd (`V4D-64`)
- Acceptance Review: https://app.notion.com/p/3aeb8344ad2c81dabfcecb8fff93f412 (`V4V-121`)
- Repository authorization: `release/V821_EXACT_PACKAGE_AUTHORIZATION.md`

## Required activation sequence

1. Publish immutable tag and GitHub Release `v8.2.1` from retained artifact `8800800923` without rebuilding.
2. Independently verify tag target, Release assets, checksums, package identities, clean installations, v8.2.0 restoration, v8.1.0 continuity, and ledger/baseline evidence.
3. Activate canonical GitHub authority with v8.2.1 Active and v8.2.0 immediate rollback.
4. Activate matching Notion System State only after GitHub activation readback.
5. Perform final live cross-authority, integration, rollback, integrity, W04-boundary, and production-ledger readback.

Publication alone does not activate production authority.

## Preserved boundaries

No autonomous scheduling, unattended provider write, messaging, email, calendar action, credential action, integration-scope expansion, Todoist task write, record deletion, profile activation, governed intent-memory inference activation, or live-network execution is authorized. Immutable v8.2.0, v8.1.0, and historical releases remain unchanged.
