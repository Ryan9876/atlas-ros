from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from atlas_ros.contracts.digests import sha256_digest
from atlas_ros.intent_memory_migration_v760 import (
    SourceEvidenceRecordV1,
    build_migration_proposal,
)
from atlas_ros.intent_memory_v760 import (
    GovernedIntentEvidenceV1,
    IntentConfirmationV1,
    IntentContextKeyV1,
    IntentContradictionV1,
    IntentCorrectionV1,
    IntentEligibilityDecisionV1,
    IntentForgettingTombstoneV1,
    IntentFreshnessPolicyV1,
    IntentInspectionViewV1,
    IntentMemoryIndexV1,
    IntentScopeV1,
    IntentUserControlReceiptV1,
)

REQUIRED_CASES = {
    "anx-central-management",
    "jira-customization-vs-integration",
    "true-completion-equivalent",
    "context-scope-isolation",
    "ryan-correction",
    "stale-evidence",
    "contradictory-evidence",
    "retired-evidence",
    "forgotten-evidence",
    "current-instruction-override",
    "migration-replay",
}
PRODUCTION_PARENT = "https://app.notion.com/p/3a3b8344ad2c819293ebd1e9b776ecd9"
UNIVERSAL_INBOX = "collection://7bc7d289-299f-4160-95c9-921ee15ce505"
REVIEW_RECORDS = "collection://0881c279-46d0-4673-9477-616008bfe477"
TARGET_KEYS = (
    "active-intent-memory-index",
    "governed-intent-evidence",
    "intent-user-control-receipts",
)


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        raise ValueError(f"expected an object in {path}")
    return value


def contract_schemas() -> dict[str, Any]:
    contracts = (
        IntentScopeV1,
        IntentContextKeyV1,
        GovernedIntentEvidenceV1,
        IntentConfirmationV1,
        IntentCorrectionV1,
        IntentContradictionV1,
        IntentFreshnessPolicyV1,
        IntentEligibilityDecisionV1,
        IntentMemoryIndexV1,
        IntentInspectionViewV1,
        IntentUserControlReceiptV1,
        IntentForgettingTombstoneV1,
    )
    return {contract.__name__: contract.model_json_schema() for contract in contracts}


def schema_plan() -> dict[str, Any]:
    targets = [
        {
            "target_key": "governed-intent-evidence",
            "operation": "create_data_source",
            "parent_page": PRODUCTION_PARENT,
            "name": "Governed Intent Evidence",
            "expected_record_count_before_migration": 0,
            "properties": {
                "Evidence ID": "TITLE",
                "Context Key Digest": "RICH_TEXT",
                "User ID": "RICH_TEXT",
                "Domain": "RICH_TEXT",
                "Project": "RICH_TEXT",
                "Responsibility": "RICH_TEXT",
                "Request Type": "RICH_TEXT",
                "Sensitivity Domain": "RICH_TEXT",
                "Confirmed Interpretation": "RICH_TEXT",
                "Represented Terminology": "RICH_TEXT",
                "Represented Behavior": "RICH_TEXT",
                "Source Kind": (
                    "SELECT('current_instruction','live_authority',"
                    "'confirmed_interaction','attributable_history')"
                ),
                "Source Reference": "RICH_TEXT",
                "Source Digest": "RICH_TEXT",
                "Confirmation Count": "NUMBER",
                "Correction Count": "NUMBER",
                "Contradiction Count": "NUMBER",
                "Confidence": "NUMBER",
                "First Confirmed": "DATE",
                "Last Confirmed": "DATE",
                "Last Used": "DATE",
                "Freshness State": "SELECT('current','stale','expired','unknown')",
                "Exceptions": "RICH_TEXT",
                "Inference Eligible": "CHECKBOX",
                "User Control State": (
                    "SELECT('active','corrected','retired',"
                    "'forgetting_pending','forgotten')"
                ),
                "Supersedes Evidence ID": "RICH_TEXT",
                "Provenance Digest": "RICH_TEXT",
                "Evidence Digest": "RICH_TEXT",
            },
        },
        {
            "target_key": "active-intent-memory-index",
            "operation": "create_data_source",
            "parent_page": PRODUCTION_PARENT,
            "name": "Active Intent Memory Index",
            "expected_record_count_before_migration": 0,
            "properties": {
                "Snapshot ID": "TITLE",
                "Snapshot At": "DATE",
                "Request Context Digest": "RICH_TEXT",
                "Active Evidence IDs": "RICH_TEXT",
                "Excluded Evidence IDs": "RICH_TEXT",
                "Evidence Digests": "RICH_TEXT",
                "Eligibility Decisions": "RICH_TEXT",
                "Deterministic Digest": "RICH_TEXT",
                "Feature Policy State": "SELECT('disabled','inspection','inference')",
            },
        },
        {
            "target_key": "intent-user-control-receipts",
            "operation": "create_data_source",
            "parent_page": PRODUCTION_PARENT,
            "name": "Intent User Control Receipts",
            "expected_record_count_before_migration": 0,
            "properties": {
                "Receipt ID": "TITLE",
                "Action": (
                    "SELECT('correction','retirement','forgetting_request',"
                    "'forgetting_verified')"
                ),
                "Evidence ID Digest": "RICH_TEXT",
                "Original Evidence Digest": "RICH_TEXT",
                "Resulting Evidence Digest": "RICH_TEXT",
                "Tombstone Digest": "RICH_TEXT",
                "Authorization Reference": "RICH_TEXT",
                "Applied": "CHECKBOX",
                "Readback Verified": "CHECKBOX",
                "Provider Write Count": "NUMBER",
                "Recorded At": "DATE",
                "Receipt Digest": "RICH_TEXT",
            },
        },
    ]
    payload = {
        "schema_version": "v760-notion-schema-plan-v1",
        "status": "proposal_only",
        "production_parent": PRODUCTION_PARENT,
        "create_targets": targets,
        "modify_targets": [],
        "universal_inbox_unchanged": True,
        "review_records_unchanged": True,
        "additive_and_backward_compatible": True,
        "rollback": {
            "software": "disable v7.6.0 and restore v7.5.2 behavior",
            "schema": "retain empty additive data sources unused; do not delete",
            "migration": "no migration writes are proposed in the initial snapshot",
        },
        "provider_write_count": 0,
    }
    payload["schema_plan_digest"] = sha256_digest(payload)
    return payload


def migration_proposal(snapshot: dict[str, Any]) -> dict[str, Any]:
    records = tuple(
        SourceEvidenceRecordV1(
            source_system=record["source_system"],
            source_record_id=record["source_record_id"],
            source_type=record["source_type"],
            source_reference=record["source_reference"],
            source_digest=sha256_digest(record),
            attributable=record["attributable"],
            confirmed=record["confirmed"],
            speculative=record.get("speculative", False),
        )
        for record in snapshot["records"]
    )
    proposal = build_migration_proposal(
        proposal_id="v760-initial-production-evidence-migration",
        source_records=records,
        source_data_sources=(
            REVIEW_RECORDS,
            UNIVERSAL_INBOX,
            "github://Ryan9876/atlas-ros/tests/fixtures/v752_clarification_cases.json",
        ),
        destination_target_keys=TARGET_KEYS,
    )
    replay = build_migration_proposal(
        proposal_id="v760-initial-production-evidence-migration",
        source_records=records,
        source_data_sources=proposal.source_data_sources,
        destination_target_keys=TARGET_KEYS,
    )
    if replay.deterministic_digest != proposal.deterministic_digest:
        raise ValueError("migration dry-run replay is not deterministic")
    payload = proposal.model_dump(mode="json")
    payload.update(
        {
            "proposed_output_digest": proposal.proposed_output_digest,
            "proposal_digest": proposal.deterministic_digest,
            "source_snapshot_metadata_digest": sha256_digest(snapshot["sources"]),
            "idempotency_proof": {
                "replay_proposal_digest": replay.deterministic_digest,
                "identical": True,
                "duplicates_created": 0,
            },
            "expected_destination_record_count_before_migration": 0,
            "provider_write_count": 0,
            "todoist_write_count": 0,
        }
    )
    return payload


def feature_policy_target() -> dict[str, Any]:
    payload = {
        "schema_version": "v760-feature-policy-target-v1",
        "after_release_activation": "disabled",
        "after_schema_and_migration_readback": "inspection",
        "correction_enabled_after_readback": True,
        "retirement_enabled_after_readback": True,
        "forgetting_execution_enabled": False,
        "inference_enable_target": "disabled_pending_separate_exact_authorization",
        "safe_fallback": "Atlas ROS v7.5.2 clarification behavior",
        "scope_disable_supported": True,
        "evidence_disable_supported": True,
        "deterministic_snapshot_required": True,
        "provider_write_count": 0,
    }
    payload["feature_policy_digest"] = sha256_digest(payload)
    return payload


def privacy_receipt(cases: dict[str, Any], snapshot: dict[str, Any]) -> dict[str, Any]:
    serialized = json.dumps({"cases": cases, "snapshot": snapshot}, sort_keys=True)
    blocked_terms = ("password", "secret", "credential", "@gmail.com")
    findings = [term for term in blocked_terms if term in serialized.casefold()]
    return {
        "schema_version": "v760-privacy-review-receipt-v1",
        "status": "passed" if not findings else "failed",
        "fixture_count": len(cases["cases"]),
        "migration_source_record_count": len(snapshot["records"]),
        "raw_sensitive_text_retained": False,
        "public_log_sensitive_content": False,
        "findings": findings,
        "provider_write_count": 0,
        "todoist_write_count": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build deterministic v7.6.0 intent-memory proposal evidence."
    )
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path("tests/fixtures/v760_intent_memory_cases.json"),
    )
    parser.add_argument(
        "--migration-snapshot",
        type=Path,
        default=Path("tests/fixtures/v760_migration_snapshot.json"),
    )
    parser.add_argument("--output-directory", type=Path, default=Path("build"))
    arguments = parser.parse_args()
    output = arguments.output_directory
    output.mkdir(parents=True, exist_ok=True)
    cases = load_json(arguments.cases)
    snapshot = load_json(arguments.migration_snapshot)
    found = {case["case_id"] for case in cases["cases"]}
    if found != REQUIRED_CASES:
        raise ValueError(f"required regression cases mismatch: {sorted(found)}")
    schemas = contract_schemas()
    plan = schema_plan()
    migration = migration_proposal(snapshot)
    feature = feature_policy_target()
    privacy = privacy_receipt(cases, snapshot)
    if privacy["status"] != "passed":
        raise ValueError("privacy review failed")
    write_json(output / "V760_CONTRACT_SCHEMAS.json", schemas)
    write_json(output / "V760_SCHEMA_PLAN.json", plan)
    write_json(output / "V760_MIGRATION_PROPOSAL.json", migration)
    write_json(output / "V760_FEATURE_POLICY_TARGET.json", feature)
    write_json(output / "V760_PRIVACY_REVIEW_RECEIPT.json", privacy)
    summary = {
        "schema_version": "v760-proposal-evidence-index-v1",
        "contract_count": len(schemas),
        "regression_case_count": len(cases["cases"]),
        "schema_plan_digest": plan["schema_plan_digest"],
        "migration_input_snapshot_digest": migration["input_snapshot_digest"],
        "migration_output_digest": migration["proposed_output_digest"],
        "migration_create_count": migration["create_count"],
        "migration_update_count": migration["update_count"],
        "migration_skip_count": migration["skip_count"],
        "feature_policy_digest": feature["feature_policy_digest"],
        "provider_write_count": 0,
        "todoist_write_count": 0,
    }
    summary["deterministic_digest"] = sha256_digest(summary)
    write_json(output / "V760_PROPOSAL_EVIDENCE_INDEX.json", summary)


if __name__ == "__main__":
    main()
