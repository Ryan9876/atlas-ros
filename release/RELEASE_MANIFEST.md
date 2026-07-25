# Atlas ROS v6.0.0rc1 Candidate Manifest

Status: Development candidate only. Atlas ROS v5.6.0 remains the sole Active production authority.
Atlas ROS v5.5.0 remains the current immediate immutable rollback. Production promotion is not
authorized.

- Package version: `6.0.0rc1`
- Development branch: `agent/canonical-reconciliation-phase5`
- Release branch: `release/v6.0-candidate`
- Intended draft tag: `v6.0.0-rc.1`
- Current Active authority: Atlas ROS v5.6.0
- Immediate production rollback: Atlas ROS v5.5.0
- Prospective immediate rollback if promoted: Atlas ROS v5.6.0
- Production promotion authorized: No

## Scope

This candidate completes roadmap Wave 6 Canonical Reconciliation and Semantic Cutover:
Reconciliation V2 contracts and schemas; declarative field authority; deterministic
provider-neutral plans; structured conflicts; command/event idempotency; integrity-protected
checkpoints; exact-plan attended authorization; verified readback and fail-closed receipts;
bidirectional development-record reconciliation; semantic-only runtime ownership; numbered
interface retirement; breaking-change and migration guidance; differential validation; restored
artifact validation; and v5.6 rollback rehearsal.

Planning remains side-effect free. Adapters cannot plan, authorize, decide field authority, or
advance checkpoints. Reconciliation cannot create unplanned execution work. Validation uses
deterministic fakes and performs no live Todoist or Notion writes.

## Authority

GitHub remains canonical for source, architecture, schemas, release evidence, artifacts,
restoration, and historical software. Notion remains dynamic management authority. Todoist remains
attended execution authority. The fixed Google Drive Release Index remains the initialization
bootstrap. Required production integrations remain Google Drive, Notion, and Todoist.

Integration Inventory authority:
https://app.notion.com/p/8ba4fafb5ce244ef9add3013aff3746b

## Eligibility

Eligibility requires exact-head CI, release-candidate validation, 77/77 reconciliation benchmark
cases, zero unexplained differential drift, W modules absent from wheel and source distribution,
dependency/security audits, checksums, SBOM consistency, clean installation, draft publication
and authoritative readback, Drive-independent restoration, v5.6 rollback restoration,
development-record reconciliation, and Full Validation.

The readable candidate workspace is valid only when all named evidence, package assets, checksums,
restoration assets, current Active production evidence, and rollback evidence are readable,
internally consistent, checksum-valid, and successfully read back. Secrets and private signing
material are excluded.

Production promotion, final release publication, authority switching, and actual post-promotion
reconciliation remain reserved for Ryan.
