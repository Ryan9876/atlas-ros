"""Assemble the v4.1.0 restoration companion from live published authorities.

The source strings below are a faithful transcription of the published release
workspace read on 2026-07-21.  This tool intentionally does not invent the
unpublished legacy shell implementation.
"""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "release" / "atlas-ros-v4.1.0-restoration-companion"

FILES = {
    "OPERATING_CONTRACT.md": """# Atlas ROS v4 Operating Contract

## Mission
Atlas protects Ryan's focus, commitments, leadership visibility, and system reliability by converting unstructured signals into trustworthy context, decisions, and executable work.

## Authority
1. Platform and safety instructions.
2. Atlas Project bootloader.
3. Ryan's explicit current instruction.
4. Active Drive release.
5. Current Notion System State.
6. Authoritative application record for the object or field.

## Systems of record
- Drive: release, policy, standards, templates, recovery.
- Notion: Inbox, actions, delegated work, projects, risks, decisions, operations, integrations, automations, reviews.
- Todoist: completion, operational due date, execution priority, project, labels, sections, filters, and task queue.

## Required behavior
- Read before write.
- Use one authority per field.
- Verify writes by readback.
- Informational and advisory requests do not create tasks.
- Todoist creation requires explicit request, /todoist, or attended approved processing.
- Consequential, destructive, external, or attendee-affecting actions require explicit authorization.
- Missing or contradictory critical authority fails closed.
""",
    "AUTHORITY_MATRIX.md": """# Atlas ROS v4 Authority Matrix

| Category | Authority |
|---|---|
| Active and rollback release | Drive Release Index |
| Operating policy | Active Drive release |
| Current system state | Notion System State |
| Capture and routing | Notion Universal Inbox |
| Management actions | Notion Action Records |
| Delegated technical and operational outcomes | Notion Delegated Work |
| Execution state and working configuration | Todoist |
| Projects | Notion Portfolio Projects |
| Risks and blockers | Notion Risks and Blockers |
| Platform defects | Notion Operations |
| Decisions | Notion Decision Log |
| Integration status | Notion Integration Inventory |
| Automation runtime status | Notion Automation Register |
| Review evidence | Notion Review Records |

No mirror or summary overrides its authoritative source.
""",
    "INITIALIZATION.md": """# Atlas ROS v4 Initialization

## Quick initialization
1. Read the Drive Release Index.
2. Confirm one Active release and immediate rollback.
3. Read the Notion System State.
4. Read the Active release manifest.
5. Read the Integration Inventory identified by the Active release manifest. Do not use a release-specific hard-coded collection ID.
6. Confirm published workspace validity and current operating limitations.

## Status
- READY: authorities agree and required integrations are current.
- READY WITH WARNINGS: authorities agree but a non-blocking production gap is recorded.
- INITIALIZATION BLOCKED: required authority is inaccessible, stale, or contradictory.

## Full validation
Use for release, recovery, audit, destructive migration, and consequential architecture changes. Validate all active schemas, registers, published files, checksums, and rollback integrity.
""",
    "CLASSIFICATION_AND_ROUTING.md": """# Classification and Routing

Canonical classifications: Action, Delegated Work, Project, Operational Workstream, Waiting, Risk or Blocker, Decision, Reference, Archive, Discard.

Routing destinations: Action Records, Delegated Work, Portfolio Projects, Risks and Blockers, Decision Log, Reference, Archive, Discard.

Calendar routing is inactive. Todoist is not an Inbox destination; Todoist execution begins only from an approved Action Record.
""",
    "EXECUTION_STANDARD.md": """# Execution Standard

- One Action Record maps to at most one Todoist parent or standalone task.
- Approved Todoist projects: #Work and #Personal only.
- Todoist owns completion, operational due date, execution priority, project, labels, sections, filters, and task queue.
- A Todoist-bound Action Record must include a non-empty Definition of Done and Execution Ready = true.
- Approved Work sections: Leadership & Team; Operations & Follow-up; Active Projects; Development & Learning; Waiting / Follow-up.
- Approved Personal sections: Finance & Administration; Home & Family; Personal Development; Waiting / Follow-up.
- Approved execution labels: DeepWork, Next, Meeting, follow-up. The 1on1 and ROS labels are prohibited.
- Approved saved filters: Focus Today; Deep Work; This Week; Follow-ups; Unscheduled Executable Work.
- Notion owns origin, management context, Definition of Done, project/risk relations, waiting context, and sync evidence.
- Every external write requires readback and idempotency protection.
""",
    "PROJECT_AND_RISK_STANDARD.md": """# Project and Risk Standard

Projects use independent Lifecycle Status and Health. Lifecycle values: Proposed, Active, On Hold, Completed, Cancelled, Archived. Health values: Green, Yellow, Red, Not Rated.

Risks and Blockers contain Risk, Blocker, or Dependency only. Platform defects belong in Operations. Risk records retain Next Review; executable mitigation belongs in Action Records.
""",
    "INTEGRATION_AND_AUTOMATION.md": """# Integration and Automation Standard

Tool availability does not imply an active integration. Integration status requires connection, approval, acceptance, and current verification.

Autonomy levels: A0 Observe, A1 Recommend, A2 Reversible internal, A3 Consequential, A4 Prohibited.

Google Drive and Notion are required production authorities. Todoist is approved for attended execution only. Calendar and email are inactive. Outlook Email and Outlook Calendar are prohibited.

W01 Universal Capture, W02 Classification and Routing, and W03 Action-to-Todoist are retargeted, acceptance-tested, and production-active against the current v4 data-source IDs.
""",
    "RECOVERY.md": """# Recovery and Rollback

Immediate rollback is Atlas ROS v4.0.1. Rollback requires explicit Ryan authorization, Release Index and System State reconciliation, and readback verification.

Atlas ROS v3.1.2 remains an older immutable recovery baseline. If v4.1.0 authority is inaccessible or contradictory, stop consequential writes and restore v4.0.1.
""",
    "VALIDATION_REPORT.md": """# Atlas ROS v4.1.0 Production Validation

Date: 2026-07-20

## Passed
- Separate v4 Notion workspace created.
- Nine clean v4 databases created.
- Informational Inbox write/readback passed.
- Action Record write/readback passed.
- No Calendar or #ROS routing options exist in v4 Inbox.
- Project lifecycle and health are separated.
- Risks are separated from ROS platform issues.
- Drive active release folder created, promoted, and read back.
- v4.0.1 and v3.1.2 remained unchanged during release build and promotion.

## Production warning
W01, W02, W03A, and W03 are defined for attended, review-first operation. Active packaging does not change production authority or activate autonomous execution. Action Records enforce Definition of Done and Execution Ready before Todoist creation. Todoist projects, sections, labels, filters, and prohibited labels match the governed configuration.

## Rollback
Atlas ROS v4.0.1 remains immutable and is the immediate rollback.
""",
    "PATTERN_AND_DECOMPOSITION_STANDARD.md": """# AI Pattern Recognition and Continuous Optimization Standard

Pattern-to-Standard lifecycle: Observe → Qualify → Recommend → Decide → Implement → Measure → Retain, Revise, or Retire. Use existing ROS record types whenever possible; do not add a database without a distinct lifecycle and recurring need.

Work Breakdown Pattern Library: Investigation; Pilot or Deployment; Migration or Retirement; Data Reconciliation; Blocker Resolution; Vendor or Cross-Team Coordination.

W03A Action Decomposition requires Action-versus-Project confirmation, a high-confidence pattern or custom decomposition, a clear parent outcome, separation of Ryan-owned actions from Delegated Work, meaningful binary subtasks, sequence and duplicate validation, and Execution Ready only after the gate passes.
""",
    "LIFECYCLE_AND_REVIEW_STANDARD.md": """# Lifecycle and Review Standard

Readiness contracts apply to Execution Ready actions, waiting actions, assigned Delegated Work, active projects, open risks, pending decisions, production automations, and reviews passed with findings.

Cadence: P1/P2 and critical exposure daily or event-driven; open actions twice weekly; projects, decisions, risks, delegated work, and waiting items weekly; integrations, automations, data quality, pattern review, and lifecycle cleanup monthly; System State and release controls after material change.

Acceptance tests route to Review Records. Platform failures route to Operations. Temporary test tasks are identified and cleaned up during acceptance.
""",
    "RELEASE_ELIGIBILITY.md": """# Release Eligibility and Promotion Transaction

A new release is required for material changes to immutable policy, architecture, workflow contracts, schemas, integration scope, package content, or rollback integrity. Current metadata, links, relationships, status, verification dates, and views are corrected in place when authorized.

Promotion requires frozen source files, generated and independently verified SHA-256 checksums, Full Validation, Decision and Review evidence, explicit authorization, transactional Release Index and System State updates, readback, and preservation of the prior Active release as immutable rollback. Promotion fails closed on any checksum mismatch or authority contradiction.
""",
}

MANIFEST = """# Atlas ROS v4.1.0 Restoration Companion

Status: restoration companion; not a new release and does not alter the Active v4.1.0 release or its immutable v4.0.1 rollback.

Authority source: the live v4.1.0 PUBLISHED_RELEASE_WORKSPACE, RELEASE_MANIFEST, and W01 runbook were fetched from the Active Drive release on 2026-07-21.

Contents: individually materialized active policy documents, the published source checksum block, release manifest transcription, W01 runbook transcription, a fresh SHA-256 manifest, and restoration instructions.

Important limitation: the Active package did not publish the legacy `ros-capture-v1.1.5.sh`, observability script, health script, test fixtures, or source archive. This companion preserves every artifact currently readable from the Active package, but it cannot assert a reconstructed legacy executable as authentic source.
"""

RELEASE_MANIFEST = """Atlas ROS v4.1.0 Active Release Manifest

Product: Atlas Ryan Operating System
Release: 4.1.0
Status: Active; sole current production authority
Release class: Continuous optimization, decomposition, lifecycle, execution, and release-integrity standardization
Promoted: 2026-07-20 by Ryan's explicit authority after Full Validation
Current Active: Atlas ROS v4.1.0; current immediate rollback: Atlas ROS v4.0.1 — immutable
Owner and final authority: Ryan

The readable active manifest, active PUBLISHED_RELEASE_WORKSPACE document, W01 runbook, source checksum block, and linked production Notion authorities—including Delegated Work—form the active restoration representation. Independent checksum verification remains pending publication of the individual immutable source artifacts. W01-W03 are production-active in attended mode. Raw ZIP upload remains a non-blocking transport gap because the connector proxy rejects local binary upload; v4.0.1 is the immediate immutable rollback and v3.1.2 remains an older preserved recovery baseline.
"""

W01 = """# Atlas ROS v4.1.0 — W01 Universal Capture Runbook

Purpose: repeatable validation, recovery, and retargeting procedure for the production W01 Universal Capture workflow. Current runtime state and acceptance evidence are maintained in the Automation Register and Review Records.

## Target production Inbox
- Database: https://app.notion.com/p/ecc51b926f32483a86cf5d77b4eab069
- Data source: collection://7bc7d289-299f-4160-95c9-921ee15ce505

## Required properties now present
- Capture — Title
- Raw Capture — Rich text
- Source — Select with Raycast
- Status — Select with New
- Correlation ID — Rich text
- Capture ID — Rich text
- Processing Note — Rich text

## Procedure on Ryan's Mac
1. Open the existing ROS Capture Raycast Script Command.
2. Retain the approved ros-capture-v1.1.5.sh code and Keychain token handling.
3. Replace the legacy Universal Inbox database-container ID or URL with the v4 database shown above.
4. Confirm the Notion connection has access only to the v4 Universal Inbox.
5. Run three harmless captures from different applications.
6. Verify each record appears once with Source=Raycast, Status=New, Capture ID, Correlation ID, and Processing Note populated.
7. Disconnect the network, submit one harmless capture, reconnect, retry, and confirm exactly one record exists for the original Correlation ID.
8. Process one test item through W02 and verify its Destination Record URL.
9. Record acceptance evidence in v4 Review Records.

## Acceptance rule
Production activation or reactivation requires all device tests to pass, acceptance evidence to be recorded in Review Records, and the Automation Register to be updated and verified by readback.
"""


def write(name: str, text: str) -> None:
    (OUT / name).write_text(text.strip() + "\n", encoding="utf-8")


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    for name, text in FILES.items():
        write(name, text)
    write("RELEASE_MANIFEST.md", RELEASE_MANIFEST)
    write("W01_UNIVERSAL_CAPTURE_RUNBOOK.md", W01)
    write("RESTORATION_COMPANION.md", MANIFEST)
    instructions = """# Restoration Instructions

1. Verify the live Release Index still identifies v4.1.0 as Active and v4.0.1 as immutable rollback.
2. Verify this package with `sha256sum -c CHECKSUMS.sha256`.
3. Restore policy documents only to a separate recovery workspace; do not overwrite the Active release.
4. Reconcile System State and all Notion authorities by live read before enabling attended operations.
5. Do not reconstruct or deploy unpublished legacy executable source from this package. Use v4.0.1 rollback or the approved Python candidate as applicable.
"""
    write("RESTORATION_INSTRUCTIONS.md", instructions)
    lines = []
    for path in sorted(p for p in OUT.iterdir() if p.is_file()):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.name}")
    (OUT / "CHECKSUMS.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    shutil.make_archive(str(OUT), "zip", OUT.parent, OUT.name)


if __name__ == "__main__":
    main()
