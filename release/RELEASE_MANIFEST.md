# Atlas ROS v5.6.0rc1 Candidate Manifest

Status: Development candidate only. Atlas ROS v5.5.0 remains Active production authority.

- Package version: `5.6.0rc1`
- Development branch: `agent/execution-orchestration-phase4`
- Release branch: `release/v5.6-candidate`
- Intended draft tag: `v5.6.0-rc.1`
- Current Active authority: Atlas ROS v5.5.0
- Immediate immutable rollback: Atlas ROS v5.4.0
- Immediate rollback if separately promoted: Atlas ROS v5.5.0
- Production promotion authorized: No

## Scope

This candidate completes roadmap Wave 5 Execution Orchestration and Provider Separation:
immutable authorization, command, provider-operation, transaction, journal, recovery, and
receipt contracts; exact scoped attended authorization; deterministic command construction;
bounded retries; idempotent replay; uncertain-apply readback; partial-failure and compensation
handling; fail-closed receipts; content-safe evidence; Todoist and Notion execution adapters;
W03 compatibility; provider-separation architecture gates; schemas; and release-blocking
orchestration benchmarks.

Planning remains provider-neutral and cannot authorize or write. Adapters cannot plan, authorize,
or produce receipts. The orchestrator cannot add execution steps or reinterpret planning intent.
Validation uses deterministic fakes and performs no live Todoist or Notion writes.

## Authority and eligibility

GitHub remains canonical source and release authority. Notion remains dynamic management
authority; Todoist remains attended execution authority; the fixed Drive Release Index remains
bootstrap authority. Candidate eligibility requires exact-commit CI, dependency security,
package validation, 100% critical benchmark thresholds, checksum-bound draft staging and
readback, Drive-independent restoration, governed Full Validation, Notion reconciliation, and
Ryan's final review. Only Ryan may authorize production promotion.

Required production integrations remain Google Drive, Notion, and Todoist. Integration Inventory
authority: https://app.notion.com/p/8ba4fafb5ce244ef9add3013aff3746b

The readable candidate workspace is valid only when the manifest, validation evidence,
orchestration benchmark, architecture evidence, dependency-security evidence, SBOM, canonical
checksums, source distribution, wheel, candidate package, draft release assets, and restoration
receipt are readable, internally consistent, checksum-valid, and read back successfully.
Secrets and private signing material are excluded.
