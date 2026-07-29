# Atlas ROS v7.5.1 Draft Corrective Release Manifest

Status: development corrective candidate only; not authorized for immutable publication or production activation.

## Release identity

- Candidate version: `7.5.1`
- Active baseline resolved from live authority: Atlas ROS v7.5.0 at `f2a14c1e401debe77040d0db836e343be6f337e3`
- Immediate rollback resolved from live authority: Atlas ROS v7.4.5 at `88ccec11df6695b91fc2cc703105c42cd21e9f01`
- Candidate source baseline: Atlas ROS v7.5.0 exact package source commit `e5b828d40e63e6d3106ae6bddbcc08b48273f74b`
- Candidate source commit: `PENDING_FINAL_VALIDATION`
- Build artifact ID: `PENDING_FINAL_VALIDATION`
- Evidence package SHA-256: `PENDING_FINAL_VALIDATION`
- Source distribution SHA-256: `PENDING_FINAL_VALIDATION`
- Wheel SHA-256: `PENDING_FINAL_VALIDATION`
- SPDX SBOM SHA-256: `PENDING_FINAL_VALIDATION`
- Source manifest SHA-256: `PENDING_FINAL_VALIDATION`
- Build count: `PENDING_FINAL_VALIDATION`

Integration Inventory authority: https://app.notion.com/p/8ba4fafb5ce244ef9add3013aff3746b
Integration Inventory data source: collection://46af021f-eb9a-4eba-b10c-4523e70df0c3

## Corrective scope

Atlas ROS v7.5.1 corrects the v7.5.0 immutable-manifest omission that prevents the initializer from resolving the authoritative Integration Inventory. The corrective package:

1. preserves the complete v7.5.0 Adaptive Clarification and Intent Learning runtime behavior;
2. binds the Integration Inventory page and data source directly in the release manifest;
3. adds regression validation that fails closed when a candidate manifest omits or changes the binding;
4. updates candidate package identity from `7.5.0` to `7.5.1`; and
5. makes no production authority, schema, integration-scope, credential, provider-data, Todoist, messaging, calendar, scheduling, or deletion change.

## Production integrations

Required production integrations remain exactly **GitHub, Notion, and Todoist**. Each must remain connected, approved, accepted, production-current, and least-privilege verified. Google Drive remains optional and non-authoritative.

## Production schema state

Atlas ROS v7.5.1 requires no production Notion schema migration. Existing production data-source schemas and records remain unchanged. No destructive operation, property removal, record deletion, historical rewrite, or rollback reversal is authorized.

## Rollback chain after a separately authorized activation

- Immediate rollback: Atlas ROS v7.5.0 at `f2a14c1e401debe77040d0db836e343be6f337e3`
- Historical rollback: Atlas ROS v7.4.5 at `88ccec11df6695b91fc2cc703105c42cd21e9f01`
- Existing older historical rollback records remain preserved unchanged.

## Validation gates

The final immutable manifest may replace this draft only after all of the following pass for one exact build:

1. complete repository correctness, architecture, typing, lint, and test gates;
2. explicit manifest-to-Integration-Inventory binding validation;
3. build-once source and wheel creation with matching `7.5.1` identity;
4. source manifest, SPDX SBOM, nested checksums, and secret/dependency review;
5. clean installation of both source and wheel artifacts;
6. restoration verification for Active v7.5.0 and immediate rollback v7.4.5;
7. zero provider writes, Todoist writes, authority changes, schema migrations, messages, calendar actions, scheduled actions, credential actions, and deletions; and
8. a separate exact-package review and Ryan authorization before publication.

## Promotion boundary

This draft does not authorize a tag, GitHub Release, merge to production authority, Notion System State update, rollback change, or provider write. Publication and production authority activation remain separate exact transactions after independent publication readback.

## Preserved boundaries

No autonomous scheduling, messaging, email, calendar action, deletion, credential action, integration-scope expansion, Todoist write, provider schema migration, or unattended live-network execution is authorized. Immutable v7.5.0 and all historical releases remain unchanged.
