# ADR-003: GitHub-First Authority and Minimal Drive Dependency

- **Status:** Approved for implementation; not yet production authority
- **Decision owner:** Ryan Smith
- **Date:** 2026-07-24
- **Migration branch:** `migration/github-first-authority`
- **Current production authority during migration:** Atlas ROS v5.1.1

## Context

Atlas ROS currently uses Google Drive as the release authority, Notion as the dynamic management authority, Todoist as the attended execution authority, and GitHub as the software-development repository. The Drive dependency adds connector latency, duplicate publication surfaces, native-document conversion, inconsistent file semantics, and additional read/write reconciliation work.

The active release package already contains the source distribution, wheel, release manifest, SBOM, checksums, dependency evidence, restoration companion, validation evidence, schemas, tests, runbooks, and architecture documentation. These artifacts are naturally version-controlled and are better governed through immutable commits, tags, GitHub Actions, and GitHub Release assets.

## Decision

Atlas ROS will adopt a **GitHub-first authority model**.

GitHub becomes the canonical authority for:

- source code and configuration;
- architecture documentation and ADRs;
- schemas and semantic contracts;
- runbooks and restoration documentation;
- release index and release manifests;
- source and package checksums;
- SBOM and dependency-security evidence;
- release validation and calibration evidence;
- source distributions, wheels, and combined release packages through GitHub Releases;
- historical release tags and immutable release assets;
- CI, release-candidate, publication, and verification workflows;
- development-record snapshots required for release reconciliation.

Notion remains the canonical authority for **dynamic operational and management state**, including:

- System State;
- Universal Inbox and Action Records;
- Execution Steps and Delegated Work;
- Portfolio Projects, Risks and Blockers, and ROS Operations;
- Decision Log, Review Records, Automation Register, Integration Inventory, and Development Ideas.

Todoist remains the canonical authority for **attended personal execution state**.

Google Drive is reduced to an explicitly non-primary role and retained only for:

1. the fixed bootstrap `RELEASE_INDEX.md` location required by current Atlas project initialization instructions;
2. read-only legacy release folders during the migration and rollback-retention period;
3. human-sharing exports when a Google-native format is materially better for the recipient or workflow;
4. artifacts that cannot be safely or practically represented in GitHub, provided they are declared non-authoritative and linked from the canonical GitHub record.

The Drive bootstrap Release Index will eventually contain only the minimum information needed to resolve the canonical GitHub release authority. It will not duplicate the full release workspace.

## Architectural constraints

- GitHub must not replace Notion as a transactional operational database.
- GitHub Issues must not become a duplicate of Notion Action Records or Todoist execution tasks.
- Secrets, credentials, private signing material, and live tokens must not be committed. GitHub Actions secrets or an approved secret manager must be used.
- Historical Drive release folders remain unchanged until each corresponding GitHub representation is checksum-verified.
- No Drive content is deleted as part of the initial migration. Deletion or permanent archival requires a separate explicit authorization after verified cutover.
- The active release authority does not change until a governed migration release is validated and Ryan explicitly promotes it.
- The current hard-coded Drive bootstrap remains available until Atlas project instructions are changed or a later architecture decision removes the requirement.

## Target authority chain

```text
Drive bootstrap pointer
        ↓
GitHub RELEASE_INDEX.md
        ↓
Immutable Git tag and GitHub Release
        ↓
RELEASE_MANIFEST.md + checksums + release assets
        ↓
Notion System State and governed operational records
```

## Release publication model

A governed GitHub Actions workflow will:

1. validate the exact candidate commit;
2. build source and wheel artifacts;
3. generate SBOM, dependency evidence, manifests, checksums, and restoration evidence;
4. assemble the immutable combined package;
5. create or update a versioned GitHub Release from an approved tag;
6. upload all checksum-bound assets;
7. download and verify the published assets;
8. emit a publication receipt containing commit, tag, release URL, asset digests, and verification results;
9. stop before production authority updates until Ryan explicitly authorizes promotion.

## Consequences

### Benefits

- One natural home for code, documentation, package artifacts, history, and release evidence.
- Atomic commit and tag references replace loosely coupled Drive files.
- Faster and more reliable Atlas read access through the GitHub connector.
- Fewer conversion and readback paths.
- Better diffs, provenance, branch protection, CI integration, and rollback traceability.
- Reduced risk that repository state and published release documentation diverge.

### Costs and risks

- A transitional period with both GitHub and Drive representations.
- GitHub Release publication and post-publication verification must be implemented and validated.
- Binary and large-file retention policy must be governed to prevent repository bloat.
- The fixed Drive bootstrap remains a dependency until the project initialization contract changes.
- Notion-to-GitHub release snapshots require deterministic export formats and reconciliation.

## Migration completion criteria

The authority migration is complete only when:

- every authoritative Drive release artifact has a checksum-matched GitHub equivalent;
- the active and immediate rollback releases are restorable from GitHub without Drive content;
- GitHub Release publication and download verification pass;
- the GitHub Release Index, release manifest, tag, commit, and assets agree;
- Notion System State, Decision Log, Review Records, Automation Register, Integration Inventory, and Development Ideas agree with GitHub;
- the Drive bootstrap resolves the same active release and rollback;
- all Drive-only runbook and automation references are replaced or explicitly allowlisted;
- Full Validation passes;
- Ryan explicitly promotes the GitHub-first authority release.
