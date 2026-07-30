# Atlas ROS v8.0.0 Full Validation Report — Exact Candidate

Status: **PASSED** for exact package source commit `674f0c979dec8f83a1610c7435e633e2d33e673a`. This report does not authorize merge, publication, migration application, or activation.

## Exact evidence

- Full validation run: `30574165764`
- Candidate artifact ID: `8772036696`
- Candidate artifact digest: `sha256:9202086b86df6f727daa097d476a82099ebdbd97e8e85aa433160cb8f40464ea`
- Evidence completion run: `30574165698`
- Evidence artifact ID: `8771997275`
- Evidence artifact digest: `sha256:e480e5f2ecda736fdabae36e71fba3a8628e1b9e7240085a24fc8a6eda999f95`
- Validation receipt SHA-256: `49bf52c882ca99cefe9b7a3fdf02c0578124c2771c1dde59aa729534e2d6f5dd`

## Correctness gates

- Ruff: passed.
- Strict MyPy: passed.
- Architecture boundary validation: passed.
- Development-tool boundary validation: passed.
- Cookbook and shared fixture verification: passed.
- Notion migration validation: passed as `validated_unapplied`.
- Test suite: `1014 passed`, `0 failed`, `0 errors`, `0 skipped`.
- Total coverage: `86.56235017216581%`.
- Statement coverage: `90.41722745625842%`.
- Branch coverage: `70.16941391941391%`.

## Functional and safety results

- Existing explicit delegation remained compatible.
- Qualified natural updates normalized to the existing typed `delegate` command.
- Person-name mention alone did not delegate.
- `Waiting for Bill` normalized to `waiting-on`.
- Missing responsible party, governed identity, expected outcome, or completion criteria blocked provider planning.
- Delegate due date and Ryan follow-up checkpoint remained separate.
- Ambiguous date meaning failed closed.
- Explicit follow-up became the Todoist due date; compiled undated policy remained available only when permitted.
- Obsolete checkpoints were replaced; the one-active-checkpoint rule passed.
- Replay produced stable command and operation identities with zero duplicate writes.
- Parent outcomes remained open after delegation and delegated-child completion.
- Notion/Todoist identity and URL readback fixtures passed.
- Partial-failure recovery required identity readback before retry.
- Negative fixtures produced zero delegation false positives.

## Provider and migration evidence

- Provider writes: `0`.
- Notion writes: `0`.
- Todoist writes: `0`.
- Authorization ID during validation: `null`.
- Replay/idempotency: passed.
- Notion/Todoist readback fixture: passed.
- Partial-failure recovery fixture: passed.
- Unresolved person provider planning: blocked.
- Additive migration fields: `10`.
- Destructive migration operations: `0`.
- Migration live reads: `0`.
- Migration live writes: `0`.
- Production migration authorization: `false`.

## Security and dependency evidence

- Scoped secret scan: passed with `49` files scanned and `0` findings.
- PyPI dependency audit: `7` locked dependencies evaluated, `0` known vulnerabilities.
- OSV dependency audit: `7` locked dependencies evaluated, `0` known vulnerabilities.

## Exact package and installation evidence

- Build count: `1`.
- Source distribution SHA-256: `2bfd6fda0879b9508809bdb28a41f43a664bee1098ce3325b3574223cd864047`.
- Wheel SHA-256: `0a308d4b4d23a86b99fe66a1e17b89340ff5ab84091b9eca277f461d13f8f8a5`.
- Clean source-distribution installation and `atlas status`/`atlas verify`: passed.
- Clean wheel installation and `atlas status`/`atlas verify`: passed.
- SPDX SBOM SHA-256: `65c8642671b1729bb775540d7bcdb5af05d14659d39169c940b8c13b5a14d9ec`.
- Source manifest SHA-256: `667774768014e45fb821964d2c78f8225b34f74869e7e5cb7398b1d7bb79cc05`.
- Source-tree SHA-256: `a4c0ee2e4222979cbca4939fb38a405168b531f0bd6527574fe60d70205e9d8d`.

## Rollback evidence

- Live authority was read from `main` during the exact run.
- Active Atlas ROS v7.8.0 tag target and immutable manifest digest were verified.
- Published v7.8.0 source and wheel matched the digests in live authority.
- Immediate rollback Atlas ROS v7.7.0 tag target was verified.
- The v7.7.0 immutable manifest was resolved dynamically from the authority-provided commit.
- Published v7.7.0 source and wheel matched the manifest-bound digests.
- No authority or rollback record was changed.

## Production state and remaining blockers

Atlas ROS v7.8.0 remains Active. No v8.0.0 package has been merged, tagged, published, or activated. No Notion schema, Todoist task, provider record, integration scope, or production authority has been changed.

The remaining required release controls are the governing Decision, Acceptance Review, Ryan's explicit authorization of the exact retained package and sequence, immutable publication without rebuild, independent publication readback, attended migration application, authority activation, and final live readback. All remain **PENDING**.
