# ADR-004: GitHub-Only Initialization and Optional Drive History

- **Status:** Approved for v7.0.1 implementation
- **Decision owner:** Ryan Smith
- **Decision record:** V4D-40
- **Date:** 2026-07-28
- **Supersedes:** The Drive-bootstrap portions of ADR-003 and the v7.0.0 activation metadata

## Context

Atlas ROS v7 was intended to make GitHub the release and initialization authority. The v7.0.0 runtime policy and tests already rejected Google Drive as a required integration, but the activated manifest, Release Index, System State, and Integration Inventory retained the transitional Drive bootstrap. The immutable v7.0.0 production commit also lacked a self-contained v7 manifest and generated authority record suitable for GitHub-only startup.

This produced a contradiction: the code said Drive was forbidden during initialization, while live metadata still required it.

## Decision

Atlas ROS v7.0.1 will use the following startup authority chain:

```text
GitHub governance/AUTHORITY.json at current authority ref
        ↓
GitHub governance/RELEASE_INDEX.md at the same authority ref
        ↓
Versioned immutable manifest at the exact active commit
        ↓
Notion System State named by AUTHORITY.json
        ↓
Integration Inventory named by the immutable manifest
```

Initialization succeeds only when these records agree on the active release, immediate rollback, authority-model version, published-workspace validity, and exact required integration set.

The required production integrations are exactly:

- GitHub
- Notion
- Todoist

Google Drive is:

- not read during initialization;
- not a release authority;
- not a runtime authority;
- not a required integration;
- optionally accessible for non-authoritative legacy history and human-sharing use; and
- preserved unless a separate exact retirement or deletion transaction is authorized.

## Integrity model

`governance/AUTHORITY.json` is the canonical mutable pointer. It binds:

- the exact active commit and tag;
- the versioned immutable manifest path and SHA-256 digest;
- the generated GitHub Release Index digest;
- the exact source and wheel digests;
- the immediate rollback;
- the Notion System State URL; and
- the manifest-based Integration Inventory resolution rule.

The generated Release Index is read from the same current GitHub authority ref as `AUTHORITY.json`. The versioned manifest is read from the immutable active commit and verified by digest. This avoids a circular requirement that the active release commit contain a generated index pointing to itself.

## Consequences

### Benefits

- Atlas can initialize without Google Drive availability or latency.
- Release authority is fully versioned, diffable, and checksum-bound in GitHub.
- The immutable package commit contains its own versioned manifest.
- Required integration scope is explicit and testable.
- Drive history can be preserved without affecting startup correctness.

### Costs and risks

- The Integration Inventory needs an explicit required-for-initialization field.
- The external ChatGPT Atlas project instruction must be updated to the GitHub-only sequence through a supported platform control or manually by Ryan.
- v7.0.0 remains the rollback-compatible production release until v7.0.1 completes exact validation, authorization, publication, and activation.

## Non-goals

This decision does not authorize:

- deletion or retirement of Google Drive content;
- credential revocation;
- integration permission expansion;
- Todoist scope changes;
- autonomous scheduling, messaging, email, calendar, or live-network execution; or
- publication or production activation without exact-package authorization.

## Acceptance criteria

- The runtime reads no Drive authority during initialization.
- The exact required integration set is GitHub, Notion, and Todoist.
- A required Drive record causes initialization to fail.
- A disconnected optional Drive record does not block initialization.
- The generated GitHub Release Index is digest-bound to `AUTHORITY.json`.
- The immutable versioned manifest is digest-bound and resolved from the exact active commit.
- Full package validation and immutable v7.0.0/v6.5.0 restoration pass.
- Live System State and Integration Inventory are updated only after authorized v7.0.1 publication and independent readback.
