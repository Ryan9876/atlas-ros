from __future__ import annotations

import pytest

from atlas_ros.devtools_cli.contracts import AuthorityDeclaration, FeatureImplementationContractV1
from atlas_ros.devtools_cli.impact import assess_changes
from atlas_ros.devtools_cli.validation import validate


def valid_contract(**overrides: object) -> FeatureImplementationContractV1:
    payload: dict[str, object] = {
        "feature_id": "advisory-demo",
        "feature_name": "Advisory demo",
        "target_release": "7.4.0",
        "category": "advisory",
        "business_objective": "Demonstrate governed contracts",
        "user_visible_outcome": "Validated feature specification",
        "invariants": ["no provider writes"],
        "prohibited_behaviors": ["production mutation"],
        "required_scenario_categories": ["deterministic_replay"],
        "acceptance_criteria": ["stable digest"],
        "release_impact": "development tooling only",
        "documentation_impact": "developer guide",
    }
    payload.update(overrides)
    return FeatureImplementationContractV1.model_validate(payload)


def test_contract_digest_is_stable() -> None:
    assert valid_contract().digest() == valid_contract().digest()


def test_contract_cannot_grant_authority() -> None:
    with pytest.raises(ValueError):
        AuthorityDeclaration(provider_writes="unattended")


def test_execution_contract_requires_readback_and_idempotency() -> None:
    with pytest.raises(ValueError):
        valid_contract(category="execution_intent")


def test_unknown_path_broadens_shadow_validation() -> None:
    result = assess_changes(["unexpected.bin"])
    assert result.mode == "shadow"
    assert result.risk_classification == "broad"
    assert "complete-candidate-gates" in result.broadened_validation
    assert result.suppresses_mandatory_gates is False


def test_governance_change_is_broad() -> None:
    assert assess_changes(["governance/architecture.yaml"]).clean_build_required is True


def test_validation_planning_does_not_execute() -> None:
    receipt = validate("candidate", execute=False)
    assert receipt.mode == "plan"
    assert receipt.provider_writes == 0
    assert receipt.candidate_freeze_permitted is False
