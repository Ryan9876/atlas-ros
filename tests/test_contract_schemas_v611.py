import json
from pathlib import Path

from atlas_ros.contracts import (
    BenchmarkExecutionPolicyV1,
    ConfidenceDimensionV1,
    HorizonPromotionProposalV1,
    ManagementPackageV3,
    ReasoningCoherenceResultV1,
    ReasoningPackageV4,
)

SCHEMAS = {
    Path("schemas/reasoning/confidence-dimension-v1.schema.json"): ConfidenceDimensionV1,
    Path("schemas/reasoning/reasoning-coherence-result-v1.schema.json"): ReasoningCoherenceResultV1,
    Path("schemas/benchmark/benchmark-execution-policy-v1.schema.json"): BenchmarkExecutionPolicyV1,
    Path("schemas/planning/horizon-promotion-proposal-v1.schema.json"): HorizonPromotionProposalV1,
    Path("schemas/reasoning-package-v4.schema.json"): ReasoningPackageV4,
}


def test_v611_schema_files_are_valid_json() -> None:
    for path in (*SCHEMAS, Path("schemas/management-package-v3.schema.json")):
        assert isinstance(json.loads(path.read_text(encoding="utf-8")), dict)


def test_new_standalone_schemas_match_contract_titles() -> None:
    for path, model in SCHEMAS.items():
        checked_in = json.loads(path.read_text(encoding="utf-8"))
        generated = model.model_json_schema()
        assert checked_in["title"] == generated["title"]


def test_management_schema_remains_readable_during_compatible_patch() -> None:
    checked_in = json.loads(
        Path("schemas/management-package-v3.schema.json").read_text(encoding="utf-8")
    )
    generated = ManagementPackageV3.model_json_schema()
    assert checked_in["title"] == generated["title"]
    assert "reasoning_coherence" in generated["properties"]
