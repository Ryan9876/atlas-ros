# Atlas ROS v7.5.1 Corrective Release-Candidate Review

## Result

A non-publishing corrective candidate has been prepared to repair the manifest-to-Integration-Inventory authority chain. Atlas ROS v7.5.0 remains the sole Active production release. No production authority, Notion System State, Integration Inventory, schema, credentials, provider data, Todoist, messaging, calendar, scheduling, or immutable release was changed.

## Root cause

The immutable Atlas ROS v7.5.0 manifest declares the required production integrations but omits both supported Integration Inventory markers:

- `Integration Inventory authority: https://...`
- `Integration Inventory data source: collection://...`

The v7 initializer resolves the Inventory exclusively from one of those manifest markers and therefore fails closed with `active manifest does not provide the Integration Inventory reference`.

## Corrective scope

1. Preserve the full v7.5.0 Adaptive Clarification and Intent Learning implementation.
2. Increment package identity to `7.5.1`.
3. Add an explicit immutable-manifest binding to:
   - Integration Inventory page: `https://app.notion.com/p/8ba4fafb5ce244ef9add3013aff3746b`
   - Integration Inventory data source: `collection://46af021f-eb9a-4eba-b10c-4523e70df0c3`
4. Add fail-closed regression tests for missing or altered manifest binding.
5. Add a build-once, clean-install, restoration, checksum, SBOM, security, and zero-write validation workflow.
6. Stop before publication, tag creation, authority activation, or Notion System State changes.

## Authority and rollback

- Current Active: Atlas ROS v7.5.0 at `f2a14c1e401debe77040d0db836e343be6f337e3`
- Current immediate rollback: Atlas ROS v7.4.5 at `88ccec11df6695b91fc2cc703105c42cd21e9f01`
- Intended immediate rollback after a separately authorized v7.5.1 activation: Atlas ROS v7.5.0
- Immutable v7.5.0 and older release records remain unchanged.

## Validation plan

The corrective workflow must validate one exact candidate commit and produce retained evidence for:

- ruff, strict MyPy, architecture and devtools boundaries, and full pytest coverage;
- exact Integration Inventory page and data-source binding;
- secret scan and locked dependency audits;
- one source distribution and one wheel with `7.5.1` identity;
- source manifest, SPDX SBOM, nested SHA-256 checksums, and build count `1`;
- clean installation and runtime identity verification for both artifacts;
- restoration and checksum verification for Active v7.5.0 and rollback v7.4.5; and
- zero provider writes, Todoist writes, authority changes, schema migrations, publications, tag changes, integration expansion, credential actions, messages, calendar actions, scheduled actions, and deletions.

## Validation status

- Source change prepared: complete.
- Draft corrective manifest prepared: complete.
- Regression tests prepared: complete.
- Governed validation workflow prepared: complete.
- Repository and exact-package CI result: pending pull-request execution.
- Exact package source commit: pending successful validation.
- Retained artifact ID and digest: pending successful validation.
- Source distribution, wheel, SBOM, and source-manifest digests: pending successful validation.
- Independent publication readback: not started and not authorized.
- Production activation: not started and not authorized.

## Promotion boundary

A successful candidate workflow does not authorize publication. After exact evidence exists, Ryan must separately authorize the exact v7.5.1 package identity before any immutable tag or GitHub Release is created. Publication must then be independently verified before a separate canonical GitHub and Notion authority activation transaction.

## Completed writes in this candidate transaction

- GitHub corrective branch and candidate files only.
- Provider data writes: `0`.
- Notion writes: `0`.
- Todoist writes: `0`.
- Messages, email, calendar, or scheduled operations: `0`.
- Records deleted: `0`.
- Credentials changed: `false`.
- Integration scope expanded: `false`.
