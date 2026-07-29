from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest
from pydantic import ValidationError

from atlas_ros.contracts.digests import sha256_digest
from atlas_ros.intent_memory_migration_v760 import (
    MigrationDisposition,
    SourceEvidenceRecordV1,
    adapt_v750_evidence,
    adapt_v752_event,
    build_migration_proposal,
)
from atlas_ros.intent_memory_policy_v760 import IntentMemoryFeaturePolicyV760
from atlas_ros.intent_memory_v760 import (
    EligibilityStatus,
    EvidenceSourceKind,
    FeatureMode,
    FreshnessState,
    GovernedIntentEvidenceV1,
    IntentContextKeyV1,
    IntentContradictionV1,
    IntentFreshnessPolicyV1,
    IntentScopeV1,
    IntentUserControlReceiptV1,
    UserControlAction,
    UserControlState,
    build_intent_memory_index,
    correct_intent_evidence,
    decide_intent_eligibility,
    evidence_precedence,
    freshness_state,
    inspect_intent_evidence,
    record_verified_forgetting,
    request_forgetting,
    retire_intent_evidence,
)

NOW = "2026-07-29T20:00:00Z"
SOURCE_DIGEST = "a" * 64


def scope(*, domain: str = "network", project: str = "ANX", sensitivity: str | None = None) -> IntentScopeV1:
    return IntentScopeV1(
        user_id="ryan",
        domain=domain,
        project=project,
        responsibility="network-services",
        request_type="classification",
        sensitivity_domain=sensitivity,
    )


def context(*, domain: str = "network", project: str = "ANX", sensitivity: str | None = None) -> IntentContextKeyV1:
    return IntentContextKeyV1(
        context_id=f"{domain}:{project}",
        scope=scope(domain=domain, project=project, sensitivity=sensitivity),
        terminology=("management", "anx"),
        behavior="treat central management as a separate outcome",
    )


def evidence(**updates: object) -> GovernedIntentEvidenceV1:
    values: dict[str, object] = {
        "evidence_id": "evidence-anx-central-management",
        "context_key": context(),
        "confirmed_interpretation": "central management is separate from naming and discovery",
        "represented_terminology": ("anx", "central management"),
        "represented_behavior": "separate outcome",
        "source_kind": EvidenceSourceKind.CONFIRMED_INTERACTION,
        "source_reference": "notion://confirmation/1",
        "source_digest": SOURCE_DIGEST,
        "confirmation_count": 3,
        "correction_count": 0,
        "contradiction_count": 0,
        "confidence": 0.9,
        "first_confirmed_at": "2026-07-01T12:00:00Z",
        "last_confirmed_at": "2026-07-28T12:00:00Z",
        "last_used_at": "2026-07-28T13:00:00Z",
        "freshness_state": FreshnessState.CURRENT,
        "inference_eligible": True,
        "provenance": ("confirmed-response",),
    }
    values.update(updates)
    return GovernedIntentEvidenceV1(**values)


def policy() -> IntentFreshnessPolicyV1:
    return IntentFreshnessPolicyV1(
        policy_id="default-v760",
        current_days=30,
        stale_days=90,
        max_inference_age_days=180,
    )


def test_scope_isolation_blocks_cross_project_domain_and_sensitive_transfer() -> None:
    base = scope()
    assert base.applies_to(scope())
    assert not base.applies_to(scope(project="Atlas ROS"))
    assert not base.applies_to(scope(domain="personal", project="Family"))
    financial = scope(domain="financial", project="Budget", sensitivity="financial")
    assert not base.applies_to(financial)
    assert base.deterministic_digest == scope().deterministic_digest


def test_context_terms_are_normalized_and_digest_is_deterministic() -> None:
    key = IntentContextKeyV1(context_id="x", scope=scope(), terminology=(" ANX ", "management", "anx"))
    assert key.terminology == ("anx", "management")
    assert len(key.deterministic_digest) == 64


def test_evidence_rejects_ineligible_state_inconsistencies_and_naive_time() -> None:
    with pytest.raises(ValidationError, match="non-current evidence"):
        evidence(freshness_state=FreshnessState.STALE)
    with pytest.raises(ValidationError, match="non-active evidence"):
        evidence(user_control_state=UserControlState.RETIRED)
    with pytest.raises(ValidationError, match="timezone"):
        evidence(first_confirmed_at="2026-07-01T12:00:00")


def test_freshness_policy_and_windows() -> None:
    assert freshness_state(last_confirmed_at="2026-07-28T20:00:00Z", now=NOW, policy=policy()) is FreshnessState.CURRENT
    assert freshness_state(last_confirmed_at="2026-05-15T20:00:00Z", now=NOW, policy=policy()) is FreshnessState.STALE
    assert freshness_state(last_confirmed_at="2026-01-01T20:00:00Z", now=NOW, policy=policy()) is FreshnessState.EXPIRED
    assert freshness_state(last_confirmed_at="2026-08-01T20:00:00Z", now=NOW, policy=policy()) is FreshnessState.UNKNOWN
    with pytest.raises(ValidationError, match="monotonically"):
        IntentFreshnessPolicyV1(policy_id="bad", current_days=90, stale_days=30, max_inference_age_days=180)


def test_precedence_and_explicit_overrides() -> None:
    item = evidence()
    assert evidence_precedence(EvidenceSourceKind.CURRENT_INSTRUCTION) == 1
    assert evidence_precedence(EvidenceSourceKind.LIVE_AUTHORITY) == 2
    assert evidence_precedence(EvidenceSourceKind.CONFIRMED_INTERACTION) == 3
    assert evidence_precedence(EvidenceSourceKind.ATTRIBUTABLE_HISTORY) == 4
    current = decide_intent_eligibility(
        evidence=item,
        request_context=context(),
        policy=policy(),
        feature_mode=FeatureMode.INFERENCE,
        now=NOW,
        current_instruction_present=True,
    )
    assert current.status is EligibilityStatus.OVERRIDDEN
    assert current.current_instruction_override
    authority = decide_intent_eligibility(
        evidence=item,
        request_context=context(),
        policy=policy(),
        feature_mode=FeatureMode.INFERENCE,
        now=NOW,
        live_authority_present=True,
    )
    assert authority.live_authority_override


def test_current_confirmed_scoped_evidence_is_eligible() -> None:
    decision = decide_intent_eligibility(
        evidence=evidence(),
        request_context=context(),
        policy=policy(),
        feature_mode=FeatureMode.INFERENCE,
        now=NOW,
    )
    assert decision.status is EligibilityStatus.ELIGIBLE
    assert decision.reason_codes == ("confirmed_current_scoped_evidence",)
    assert decision.provider_write_count == 0


def test_disabled_scope_stale_contradictory_and_cross_context_evidence_are_not_eligible() -> None:
    item = evidence(contradiction_count=2, correction_count=0)
    decision = decide_intent_eligibility(
        evidence=item,
        request_context=context(project="Atlas ROS"),
        policy=policy(),
        feature_mode=FeatureMode.INSPECTION,
        now="2026-12-31T20:00:00Z",
        consequential=True,
        scope_disabled=True,
        evidence_disabled=True,
    )
    assert decision.status is EligibilityStatus.CLARIFICATION_REQUIRED
    assert set(decision.reason_codes) >= {
        "inference_disabled",
        "scope_disabled",
        "evidence_disabled",
        "context_scope_mismatch",
        "evidence_expired",
        "unresolved_contradiction",
    }


def test_historical_evidence_cannot_control_consequential_classification() -> None:
    item = evidence(source_kind=EvidenceSourceKind.ATTRIBUTABLE_HISTORY)
    decision = decide_intent_eligibility(
        evidence=item,
        request_context=context(),
        policy=policy(),
        feature_mode=FeatureMode.INFERENCE,
        now=NOW,
        consequential=True,
    )
    assert decision.status is EligibilityStatus.CLARIFICATION_REQUIRED
    assert "historical_evidence_cannot_control_consequential_classification" in decision.reason_codes


def test_correction_preserves_original_and_creates_deterministic_successor_and_receipt() -> None:
    original, successor, correction, receipt = correct_intent_evidence(
        evidence=evidence(),
        corrected_evidence_id="evidence-anx-central-management-corrected",
        corrected_interpretation="central management means configuration management only",
        corrected_at=NOW,
        source_reference="current-interaction://correction",
        source_digest="b" * 64,
        correction_id="correction-1",
        receipt_id="receipt-correction-1",
    )
    assert original.user_control_state is UserControlState.CORRECTED
    assert not original.inference_eligible
    assert successor.supersedes_evidence_id == original.evidence_id
    assert successor.source_kind is EvidenceSourceKind.CURRENT_INSTRUCTION
    assert correction.original_evidence_digest == evidence().deterministic_digest
    assert receipt.applied and receipt.readback_verified
    assert len(receipt.deterministic_digest) == 64


def test_retirement_and_forgetting_request_exclude_evidence_without_claiming_deletion() -> None:
    retired, retirement_receipt = retire_intent_evidence(evidence=evidence(), receipt_id="retire-1", recorded_at=NOW)
    assert retired.user_control_state is UserControlState.RETIRED
    assert retirement_receipt.action is UserControlAction.RETIREMENT
    pending, request_receipt = request_forgetting(evidence=evidence(), receipt_id="forget-1", recorded_at=NOW)
    assert pending.user_control_state is UserControlState.FORGETTING_PENDING
    assert not request_receipt.applied
    assert request_receipt.provider_write_count == 0


def test_verified_forgetting_requires_authorization_provider_mutation_and_readback() -> None:
    with pytest.raises(ValueError, match="exact authorization"):
        record_verified_forgetting(
            evidence=evidence(),
            tombstone_id="t1",
            receipt_id="r1",
            exact_authorization_reference="",
            provider_readback_digest="c" * 64,
            recorded_at=NOW,
            provider_write_count=1,
        )
    with pytest.raises(ValueError, match="provider mutation"):
        record_verified_forgetting(
            evidence=evidence(),
            tombstone_id="t1",
            receipt_id="r1",
            exact_authorization_reference="decision://exact",
            provider_readback_digest="c" * 64,
            recorded_at=NOW,
            provider_write_count=0,
        )
    tombstone, receipt = record_verified_forgetting(
        evidence=evidence(),
        tombstone_id="t1",
        receipt_id="r1",
        exact_authorization_reference="decision://exact",
        provider_readback_digest="c" * 64,
        recorded_at=NOW,
        provider_write_count=2,
    )
    assert not tombstone.contains_evidence_content
    assert receipt.action is UserControlAction.FORGETTING_VERIFIED
    assert receipt.readback_verified


def test_receipt_validator_rejects_unverified_forgetting_claim() -> None:
    with pytest.raises(ValidationError, match="exact authorization"):
        IntentUserControlReceiptV1(
            receipt_id="bad",
            action=UserControlAction.FORGETTING_VERIFIED,
            evidence_id_digest="a" * 64,
            original_evidence_digest="b" * 64,
            tombstone_digest="c" * 64,
            applied=True,
            readback_verified=True,
            provider_write_count=1,
            recorded_at=NOW,
        )


def test_index_and_inspection_are_deterministic_and_exclude_retired_evidence() -> None:
    active = evidence(evidence_id="active")
    retired = evidence(evidence_id="retired", inference_eligible=False, user_control_state=UserControlState.RETIRED)
    active_decision = decide_intent_eligibility(
        evidence=active, request_context=context(), policy=policy(), feature_mode=FeatureMode.INFERENCE, now=NOW
    )
    retired_decision = decide_intent_eligibility(
        evidence=retired, request_context=context(), policy=policy(), feature_mode=FeatureMode.INFERENCE, now=NOW
    )
    index = build_intent_memory_index(
        snapshot_id="snapshot-1",
        snapshot_at=NOW,
        request_context=context(),
        evidence_items=(retired, active),
        decisions=(retired_decision, active_decision),
    )
    assert index.active_evidence_ids == ("active",)
    assert index.excluded_evidence_ids == ("retired",)
    assert index == build_intent_memory_index(
        snapshot_id="snapshot-1",
        snapshot_at=NOW,
        request_context=context(),
        evidence_items=(active, retired),
        decisions=(active_decision, retired_decision),
    )
    view = inspect_intent_evidence(active, active_decision)
    assert view.interpreted_pattern == active.confirmed_interpretation
    with pytest.raises(ValueError, match="must match"):
        inspect_intent_evidence(active, retired_decision)
    with pytest.raises(ValueError, match="exactly one"):
        build_intent_memory_index(
            snapshot_id="bad",
            snapshot_at=NOW,
            request_context=context(),
            evidence_items=(active,),
            decisions=(),
        )


def test_contradiction_requires_resolution_reference() -> None:
    with pytest.raises(ValidationError, match="resolution reference"):
        IntentContradictionV1(
            contradiction_id="c1",
            evidence_id="e1",
            conflicting_interpretation="different",
            detected_at=NOW,
            source_reference="interaction://1",
            resolved=True,
        )


def test_feature_policy_preserves_predecessor_fallback_and_inspection_controls() -> None:
    item = evidence()
    disabled = IntentMemoryFeaturePolicyV760()
    decision = disabled.evaluate(evidence=item, request_context=context(), freshness_policy=policy(), now=NOW)
    assert decision.status is EligibilityStatus.INELIGIBLE
    assert disabled.inspect(evidence=item, decision=decision) is None
    assert disabled.resolve_or_fallback(decision=decision, inferred=lambda: "v760", predecessor=lambda: "v752") == "v752"
    enabled = IntentMemoryFeaturePolicyV760(mode=FeatureMode.INFERENCE)
    eligible = enabled.evaluate(evidence=item, request_context=context(), freshness_policy=policy(), now=NOW)
    assert enabled.inspect(evidence=item, decision=eligible) is not None
    assert enabled.resolve_or_fallback(decision=eligible, inferred=lambda: "v760", predecessor=lambda: "v752") == "v760"


@dataclass
class OldEvidence:
    evidence_id: str = "old-1"
    context_key: str = "anx"
    interpretation: str = "separate outcome"
    confirmed: bool = True
    corrected_by_user: bool = False
    stale: bool = False
    contradictory: bool = False


@dataclass
class OldEvent:
    operation_id: str = "op-1"
    correlation_id: str = "corr-1"
    initial_decision_digest: str = "d" * 64
    user_response: str | None = "yes"
    final_confirmed_interpretation: str | None = "separate outcome"


def test_predecessor_adapters_preserve_sources_and_exclude_unqualified_evidence() -> None:
    adapted = adapt_v750_evidence(
        OldEvidence(),
        scope=scope(),
        source_reference="github://v750/old-1",
        source_digest="e" * 64,
        confirmed_at=NOW,
    )
    assert adapted is not None
    assert adapted.source_kind is EvidenceSourceKind.ATTRIBUTABLE_HISTORY
    assert adapt_v750_evidence(
        OldEvidence(stale=True),
        scope=scope(),
        source_reference="github://v750/stale",
        source_digest="e" * 64,
        confirmed_at=NOW,
    ) is None
    event = adapt_v752_event(
        OldEvent(),
        scope=scope(),
        source_reference="github://v752/op-1",
        source_digest="f" * 64,
        confirmed_at=NOW,
    )
    assert event is not None
    assert event.provenance[0] == "d" * 64
    assert adapt_v752_event(
        OldEvent(user_response=None),
        scope=scope(),
        source_reference="github://v752/no-response",
        source_digest="f" * 64,
        confirmed_at=NOW,
    ) is None


def test_migration_is_deterministic_idempotent_and_provider_write_free() -> None:
    eligible_record = SourceEvidenceRecordV1(
        source_system="notion",
        source_record_id="confirmed-1",
        source_type="confirmed_clarification",
        source_reference="notion://confirmed-1",
        source_digest="1" * 64,
        attributable=True,
        confirmed=True,
        interpretation="separate outcome",
        occurred_at=NOW,
        context=context(),
    )
    skipped_records = (
        SourceEvidenceRecordV1(source_system="fixture", source_record_id="synthetic", source_type="fixture", source_reference="fixture://1", source_digest="2" * 64, attributable=True, confirmed=False, speculative=True),
        SourceEvidenceRecordV1(source_system="unknown", source_record_id="unattributed", source_type="history", source_reference="history://1", source_digest="3" * 64, attributable=False, confirmed=True, interpretation="x", occurred_at=NOW, context=context()),
        SourceEvidenceRecordV1(source_system="notion", source_record_id="stale", source_type="history", source_reference="notion://stale", source_digest="4" * 64, attributable=True, confirmed=True, interpretation="x", occurred_at=NOW, context=context(), stale=True),
        SourceEvidenceRecordV1(source_system="notion", source_record_id="contradiction", source_type="history", source_reference="notion://contradiction", source_digest="5" * 64, attributable=True, confirmed=True, interpretation="x", occurred_at=NOW, context=context(), contradictory=True),
        SourceEvidenceRecordV1(source_system="notion", source_record_id="retired", source_type="history", source_reference="notion://retired", source_digest="6" * 64, attributable=True, confirmed=True, interpretation="x", occurred_at=NOW, context=context(), retired=True),
        SourceEvidenceRecordV1(source_system="notion", source_record_id="incomplete", source_type="history", source_reference="notion://incomplete", source_digest="7" * 64, attributable=True, confirmed=True),
    )
    first = build_migration_proposal(
        proposal_id="migration-1",
        source_records=(eligible_record, *skipped_records),
        source_data_sources=("source-a",),
        destination_target_keys=("governed-intent-evidence",),
    )
    assert first.create_count == 1
    assert first.skip_count == len(skipped_records)
    assert first.provider_write_count == first.todoist_write_count == 0
    created = next(item.proposed_evidence for item in first.items if item.disposition is MigrationDisposition.CREATE)
    assert created is not None
    replay = build_migration_proposal(
        proposal_id="migration-1-replay",
        source_records=(eligible_record, *skipped_records),
        source_data_sources=("source-a",),
        destination_target_keys=("governed-intent-evidence",),
        existing_destination_evidence_ids=(created.evidence_id,),
    )
    assert replay.create_count == 0
    assert replay.skip_count == len(first.items)
    identical = build_migration_proposal(
        proposal_id="migration-1",
        source_records=(eligible_record, *skipped_records),
        source_data_sources=("source-a",),
        destination_target_keys=("governed-intent-evidence",),
    )
    assert first.deterministic_digest == identical.deterministic_digest


def test_required_regression_cases_are_present_and_minimized() -> None:
    path = Path(__file__).parent / "fixtures" / "v760_intent_memory_cases.json"
    payload = json.loads(path.read_text())
    identifiers = {case["case_id"] for case in payload["cases"]}
    assert identifiers == {
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
    assert "email" not in path.read_text().casefold()
    assert sha256_digest(payload) == sha256_digest(json.loads(path.read_text()))
