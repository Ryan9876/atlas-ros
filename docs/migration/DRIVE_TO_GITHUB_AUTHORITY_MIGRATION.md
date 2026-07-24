# Drive-to-GitHub Authority Migration

## Objective

Move Atlas ROS software, release, documentation, validation, and recovery authority to GitHub while preserving Notion as dynamic operational authority, Todoist as attended execution authority, and only a minimal non-primary Google Drive footprint.

## Verified baseline

- Active release: Atlas ROS v5.1.1
- Validated source head: `0b8b1d73fdca887c3517e7b29dd676fbeaa2d2d2`
- Merged release commit: `c348b8b5e843acc010fe8b5f000de0aaee6187ef`
- Active package SHA-256: `35fd356a93c253142d1eea715af4753996468073977077e6a178db166b2fcd5f`
- Immediate rollback: Atlas ROS v5.1
- Current Drive root: `Atlas_ROS`
- Current GitHub repository: `Ryan9876/atlas-ros`

The active package, all 14 publication checksums, all 247 source checksum entries, and the restoration-companion checksum set were verified before this migration branch was created.

## Scope classification

### Migrate to GitHub as canonical authority

- root and release-specific Release Index files;
- release manifests and promotion records;
- combined release ZIP files;
- release-candidate ZIP files;
- source distributions and wheels;
- SBOMs, dependency locks, audit evidence, and vulnerability exceptions;
- checksum manifests and publication receipts;
- validation, calibration, and promotion-preparation reports;
- restoration companions and recovery instructions;
- architecture, policy, migration, and operating documentation;
- runbooks currently stored as Drive-native documents;
- release-history metadata required for restoration or audit.

### Remain in Notion

- dynamic System State;
- production databases and live record relationships;
- decisions, reviews, integration status, automation lifecycle, and development ideas;
- management and operational state that changes independently of a software release.

GitHub receives deterministic release snapshots of these records when required for package restoration or release reconciliation; it does not replace the live databases.

### Remain in Todoist

- current Ryan-owned execution tasks and their execution state.

### Drive retention allowlist

- the existing fixed bootstrap `RELEASE_INDEX.md` URL;
- unchanged historical release folders until checksum-matched GitHub migration is verified;
- Google-native presentation, document, or spreadsheet exports when the format itself is required for collaboration;
- explicitly approved large or externally shared artifacts that are unsuitable for GitHub, with a canonical GitHub metadata record and checksum.

Everything retained in Drive must be classified as one of:

- `bootstrap`;
- `legacy-read-only`;
- `human-sharing-export`;
- `github-unsuitable-artifact`.

Drive content outside the allowlist is a migration finding.

## Phases

### M0 — Governance and baseline

- Adopt ADR-003.
- Record the architecture and integration decisions in Notion.
- Preserve the active package and rollback unchanged.
- Inventory every direct child and nested release artifact in the Drive `Atlas_ROS` workspace.
- Create a machine-readable migration manifest with Drive ID, title, type, size, modified time, target GitHub location, checksum where available, retention class, and migration status.

**Exit:** every Drive item is classified and no item is silently omitted.

### M1 — Repository baseline correction

- Reconcile GitHub `main` to the validated v5.1.1 release lineage.
- Confirm no file difference between the reviewed source head and merged release commit.
- Add the GitHub-first authority ADR, migration plan, release-index schema, and retention allowlist.
- Add architectural fitness checks preventing new authoritative Drive links in source, release, and runbook content except allowlisted bootstrap references.

**Exit:** future work begins from a correct GitHub baseline.

### M2 — Historical authority import

For every historical Drive release folder:

- identify the corresponding Git commit, tag, or source package;
- import missing text artifacts into versioned repository history or a dedicated historical-authority tree;
- publish binary packages as versioned GitHub Release assets rather than Git blobs;
- preserve original Drive IDs and checksums in migration metadata;
- verify imported contents against original checksums or calculate and record migration checksums when no original digest exists.

Candidate or incomplete folders remain historical evidence and are clearly labeled non-production.

**Exit:** every Drive release folder has a mapped and verified GitHub representation.

### M3 — GitHub Release pipeline

Implement a governed workflow that:

- builds and validates candidates;
- creates immutable version tags;
- publishes GitHub Release assets;
- downloads all assets after publication;
- validates every checksum;
- emits a signed or checksum-bound publication receipt;
- prevents release mutation after promotion except through a governed corrective release.

The pipeline must support a preparation mode that creates evidence without promoting production authority.

**Exit:** active and rollback packages can be published and restored without Drive.

### M4 — Authority cutover candidate

- Create canonical `governance/RELEASE_INDEX.md` in GitHub.
- Update release manifests to use GitHub commit, tag, release, and asset locations.
- Create deterministic JSON or Markdown snapshots of required Notion release records.
- Update restoration instructions to begin with GitHub and use Drive only as bootstrap fallback.
- Update source validation to reject unapproved authoritative Drive dependencies.

**Exit:** a complete candidate can initialize, validate, restore, and roll back using GitHub plus live Notion records.

### M5 — Notion and integration reconciliation

After Ryan approves the candidate architecture but before promotion:

- update the Notion System State target authority model;
- add GitHub to the Integration Inventory as production release and software authority;
- change Google Drive to `contract_only` or the least privileged lifecycle state supported by the final bootstrap design;
- update Automation Register runbooks and definitions to GitHub locations;
- update Decision Log, Review Records, and Development Ideas;
- verify every write by readback.

**Exit:** GitHub, Notion, and the Drive bootstrap resolve the same candidate authority model.

### M6 — Promotion and Drive reduction

After Full Validation and Ryan's explicit promotion authorization:

- promote the GitHub-first release;
- update the fixed Drive Release Index to a minimal bootstrap pointer;
- mark historical Drive release folders `legacy-read-only`;
- stop publishing new release workspaces to Drive;
- retain only allowlisted Drive artifacts;
- produce a final migration report and exception list.

No Drive deletion occurs in this phase unless Ryan separately authorizes it after the cutover has remained stable.

## Validation requirements

- exact active-package digest verification;
- publication checksum verification;
- canonical source checksum verification;
- restoration companion verification;
- active and rollback restoration tests from GitHub;
- release-asset download and verification;
- link and authority consistency checks;
- no unapproved Drive-authority references;
- CI, strict typing, tests, coverage, build, clean install, dependency audits, SBOM consistency, and calibration;
- Notion Decision Log, Review Records, Automation Register, Integration Inventory, and Development Ideas reconciliation;
- fixed Drive bootstrap readback;
- explicit Ryan promotion decision.

## Non-goals

- moving live Notion operational records into GitHub Issues;
- moving Todoist execution state into GitHub;
- committing secrets or credentials;
- deleting historical Drive artifacts during initial migration;
- changing current production workflows while authority migration is incomplete;
- beginning the modular-engine refactor before the GitHub-first authority baseline is accepted.

## Program sequencing

```text
GitHub authority migration
        ↓
GitHub baseline and release pipeline stable
        ↓
Capability-based ROS architecture migration
        ↓
Semantic workflow cutover
```
