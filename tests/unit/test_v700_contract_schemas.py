from __future__ import annotations

import json
from pathlib import Path

from atlas_ros.contracts.compiler import compile_contract_registry
from atlas_ros.contracts.schemas import (
    expected_contract_schema,
    validate_contract_schemas,
)


def test_repository_contract_schemas_match_canonical_models() -> None:
    assert validate_contract_schemas() == []


def test_expected_schema_binds_catalog_id_version_and_path() -> None:
    registry = compile_contract_registry(Path("governance/contract-catalog.yaml"))
    descriptor = registry.require("atlas.authorized-execution-plan")
    schema = expected_contract_schema(descriptor)

    assert schema["$id"].endswith(descriptor.schema_path)
    assert schema["properties"]["contract_id"]["const"] == descriptor.contract_id
    assert schema["properties"]["schema_version"]["const"] == descriptor.schema_version


def test_schema_validation_detects_committed_drift(tmp_path: Path) -> None:
    source_root = Path(".")
    (tmp_path / "governance").mkdir()
    (tmp_path / "schemas" / "capture").mkdir(parents=True)
    catalog = source_root / "governance" / "contract-catalog.yaml"
    (tmp_path / "governance" / "contract-catalog.yaml").write_text(
        catalog.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    registry = compile_contract_registry(catalog)
    for descriptor in registry.contracts.values():
        target = tmp_path / descriptor.schema_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            (source_root / descriptor.schema_path).read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    tampered_path = tmp_path / "schemas" / "capture" / "capture-envelope.schema.json"
    tampered = json.loads(tampered_path.read_text(encoding="utf-8"))
    tampered["properties"]["content"]["maxLength"] = 1
    tampered_path.write_text(json.dumps(tampered), encoding="utf-8")

    findings = validate_contract_schemas(tmp_path)

    assert findings == [
        {
            "contract_id": "atlas.capture-envelope",
            "path": "schemas/capture/capture-envelope.schema.json",
            "rule": "committed JSON Schema differs from canonical model",
        }
    ]
