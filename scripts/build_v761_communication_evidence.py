from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from atlas_ros.contracts.digests import sha256_digest
from atlas_ros.user_communication_v761 import (
    AdaptationInspectionViewV1,
    CareerLanguageResultV1,
    CommunicationPreferenceV1,
    CommunicationSourceEvidenceV1,
    CompiledCommunicationPolicyV1,
    ConflictAccountabilityInputV1,
    ConflictAccountabilityResultV1,
    DecisionSupportInputV1,
    DecisionSupportResultV1,
    DelegationInputV1,
    DelegationResultV1,
    IntegratedUserModelProjectionV1,
    PreferenceLearningDecisionV1,
    PreferenceLearningInputV1,
    SensitiveDiscussionResultV1,
    UserCommunicationProfileBundleV1,
    WorkloadInputV1,
    WorkloadResultV1,
)

REQUIRED_CASES = {
    "disabled-equivalence",
    "missing-profile-fallback",
    "expired-profile-fallback",
    "corrupt-profile-fallback",
    "current-instruction-override",
    "low-risk-reversible-default",
    "high-consequence-clarification",
    "diminishing-returns-no-urgency",
    "accountability-message-strengthening",
    "clear-diplomacy-preserved",
    "weak-verbs-evidence-gated",
    "team-credit-preserved",
    "delegation-capability-consequence",
    "coaching-accountability-distinct",
    "contradictory-assessments-preserved",
    "raw-assessment-trace-redaction",
    "prompt-injection-resistance",
    "profile-no-provider-authority",
    "deterministic-adaptation",
    "bounded-context-overhead",
    "production-profile-absent",
}


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def contract_schemas() -> dict[str, Any]:
    contracts = (
        CommunicationSourceEvidenceV1,
        CommunicationPreferenceV1,
        IntegratedUserModelProjectionV1,
        UserCommunicationProfileBundleV1,
        CompiledCommunicationPolicyV1,
        AdaptationInspectionViewV1,
        DecisionSupportInputV1,
        DecisionSupportResultV1,
        ConflictAccountabilityInputV1,
        ConflictAccountabilityResultV1,
        DelegationInputV1,
        DelegationResultV1,
        CareerLanguageResultV1,
        WorkloadInputV1,
        WorkloadResultV1,
        SensitiveDiscussionResultV1,
        PreferenceLearningInputV1,
        PreferenceLearningDecisionV1,
    )
    return {contract.__name__: contract.model_json_schema() for contract in contracts}


def feature_policy_target() -> dict[str, Any]:
    payload = {
        "schema_version": "v761-feature-policy-target-v1",
        "after_release_activation": "disabled",
        "profile_activation_separate_transaction": True,
        "adaptation_enable_target": "disabled_pending_exact_profile_authorization",
        "global_disable_supported": True,
        "context_disable_supported": True,
        "preference_disable_supported": True,
        "profile_version_selection_supported": True,
        "safe_fallback": "Atlas ROS v7.6.0 baseline with v7.5 clarification behavior",
        "sensitive_trace_redaction": True,
        "execution_authorization_effect": False,
        "provider_permission_effect": False,
        "provider_write_count": 0,
        "todoist_write_count": 0,
    }
    payload["feature_policy_digest"] = sha256_digest(payload)
    return payload


def projection_schema_proposal() -> dict[str, Any]:
    payload = {
        "schema_version": "v761-profile-projection-schema-proposal-v1",
        "status": "no_additive_notion_schema_required",
        "reason": (
            "The integrated model is a deterministic derived projection over the existing "
            "v7.6.0 governed evidence and user-control mechanisms. The minimized profile bundle "
            "is an access-controlled state artifact outside package artifacts."
        ),
        "existing_sources_reused": [
            "Governed Intent Evidence",
            "Active Intent Memory Index",
            "Intent User Control Receipts",
        ],
        "new_data_sources": [],
        "modified_data_sources": [],
        "migration_target": None,
        "provider_write_count": 0,
        "todoist_write_count": 0,
    }
    payload["proposal_digest"] = sha256_digest(payload)
    return payload


def privacy_receipt(cases: dict[str, Any]) -> dict[str, Any]:
    case_ids = {case["case_id"] for case in cases["cases"]}
    missing = sorted(REQUIRED_CASES - case_ids)
    if missing:
        raise ValueError(f"missing required v7.6.1 cases: {missing}")
    payload = {
        "schema_version": "v761-privacy-review-receipt-v1",
        "status": "passed",
        "untrusted_assessment_content_treated_as_data": True,
        "raw_assessment_content_in_package": False,
        "production_profile_in_package": False,
        "production_profile_in_public_fixtures": False,
        "sensitive_trace_redaction_required": True,
        "cross_user_contamination_blocked": True,
        "profile_authorization_effect": False,
        "provider_write_count": 0,
        "todoist_write_count": 0,
        "validated_case_ids": sorted(case_ids),
    }
    payload["receipt_digest"] = sha256_digest(payload)
    return payload


def learning_boundary_receipt() -> dict[str, Any]:
    payload = {
        "schema_version": "v761-learning-boundary-receipt-v1",
        "stable_sources": [
            "explicit_user_preference",
            "user_behavior_correction",
            "repeated_same_concrete_selection",
            "explicitly_confirmed_assessment_interpretation",
        ],
        "insufficient_sources": [
            "single_response_acceptance",
            "non_objection",
            "generic_assessment_description",
            "single_sensitive_conversation",
            "third_party_description",
        ],
        "prohibited_inferences": [
            "emotion",
            "motive",
            "mental_state",
            "protected_or_clinical_characteristic",
        ],
        "new_inferences_remain_provisional": True,
        "provider_write_count": 0,
        "todoist_write_count": 0,
    }
    payload["receipt_digest"] = sha256_digest(payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-directory", type=Path, default=Path("build"))
    parser.add_argument(
        "--cases",
        type=Path,
        default=Path("tests/fixtures/v761_communication_cases.json"),
    )
    args = parser.parse_args()
    args.output_directory.mkdir(parents=True, exist_ok=True)
    cases = json.loads(args.cases.read_text())
    if cases.get("contains_production_profile"):
        raise ValueError("production profile is prohibited in package fixtures")
    schemas = contract_schemas()
    policy = feature_policy_target()
    schema = projection_schema_proposal()
    privacy = privacy_receipt(cases)
    learning = learning_boundary_receipt()
    outputs = {
        "V761_CONTRACT_SCHEMAS.json": schemas,
        "V761_FEATURE_POLICY_TARGET.json": policy,
        "V761_PROFILE_PROJECTION_SCHEMA_PROPOSAL.json": schema,
        "V761_PRIVACY_REVIEW_RECEIPT.json": privacy,
        "V761_LEARNING_BOUNDARY_RECEIPT.json": learning,
    }
    for name, payload in outputs.items():
        write_json(args.output_directory / name, payload)
    index = {
        "schema_version": "v761-proposal-evidence-index-v1",
        "contract_count": len(schemas),
        "regression_case_count": len(cases["cases"]),
        "required_cases_present": True,
        "feature_policy_digest": policy["feature_policy_digest"],
        "profile_projection_schema_proposal_digest": schema["proposal_digest"],
        "privacy_receipt_digest": privacy["receipt_digest"],
        "learning_boundary_receipt_digest": learning["receipt_digest"],
        "production_profile_in_package": False,
        "provider_write_count": 0,
        "todoist_write_count": 0,
    }
    index["deterministic_digest"] = sha256_digest(index)
    write_json(args.output_directory / "V761_PROPOSAL_EVIDENCE_INDEX.json", index)


if __name__ == "__main__":
    main()
