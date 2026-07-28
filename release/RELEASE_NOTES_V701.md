# Atlas ROS v7.0.1 Corrective Release Notes

Atlas ROS v7.0.1 corrects the v7.0.0 activation metadata so the implemented GitHub-first architecture is also the live startup contract.

## GitHub-only initialization

- Starts from `governance/AUTHORITY.json` in GitHub.
- Verifies the generated `governance/RELEASE_INDEX.md` from the same GitHub authority ref.
- Resolves a versioned immutable manifest from the exact active commit.
- Verifies the manifest against the SHA-256 digest stored in `AUTHORITY.json`.
- Reads Notion System State from the URL stored in `AUTHORITY.json`.
- Resolves the Integration Inventory from the immutable manifest.
- Requires exactly GitHub, Notion, and Todoist as production integrations.
- Explicitly rejects Google Drive as a required initialization authority.

## Authority integrity correction

The v7.0.0 model attempted to read the generated Release Index from the immutable active commit while that index itself identified the immutable active commit. v7.0.1 removes that circular dependency:

- mutable GitHub authority pointer and generated projection are read together from the current authority ref;
- immutable release identity and integration-inventory location are read from a versioned manifest at the active commit; and
- both projections are independently digest-bound by `AUTHORITY.json`.

## Google Drive role

Google Drive is no longer part of startup or required production integration scope. Existing content remains preserved as optional, non-authoritative legacy history or human-sharing material. This release does not delete, retire, move, or revoke access to Drive content.

## Safety boundaries

The correction adds no autonomous scheduling, messaging, email, calendar action, deletion, live-network execution, credential action, Todoist scope expansion, or unapproved provider-write capability. Existing attended authorization, exact transaction, readback, receipt, and reconciliation controls remain unchanged.

## Promotion boundary

Atlas ROS v7.0.0 remains Active until the exact v7.0.1 package passes full validation, is separately authorized by Ryan, is published immutably, is independently read back, and is activated through a governed authority transaction.
