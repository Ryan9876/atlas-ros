"""Schema generation and fail-closed equivalence checks for v7 contracts."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any, cast

from pydantic import BaseModel

from atlas_ros.contracts.compiler import compile_contract_registry
from atlas_ros.contracts.execution.payload import ProviderOperationPayload
from atlas_ros.contracts.execution.pipeline import CaptureEnvelope, PipelineRunEnvelope
from atlas_ros.contracts.execution.transaction import (
    AuthorizedExecutionPlan,
    ExecutionTransactionReceipt,
    ProposedExecutionPlan,
)
from atlas_ros.contracts.reasoning import IntentGraph
from atlas_ros.contracts.registry import ContractDescriptor

_SCHEMA_DRAFT = "https://json-schema.org/draft/2020-12/schema"
_SCHEMA_ID_BASE = "https://github.com/Ryan9876/atlas-ros/"
_MODELS: Mapping[str, type[BaseModel]] = {
    "atlas.capture-envelope": CaptureEnvelope,
    "atlas.intent-graph": IntentGraph,
    "atlas.proposed-execution-plan": ProposedExecutionPlan,
    "atlas.provider-operation-payload": ProviderOperationPayload,
    "atlas.authorized-execution-plan": AuthorizedExecutionPlan,
    "atlas.execution-transaction-receipt": ExecutionTransactionReceipt,
    "atlas.pipeline-run-envelope": PipelineRunEnvelope,
}


class ContractSchemaError(ValueError):
    """Raised when the catalog, model, and committed schema disagree."""


def expected_contract_schema(descriptor: ContractDescriptor) -> dict[str, Any]:
    """Generate the canonical JSON Schema for one catalog descriptor."""
    try:
        model = _MODELS[descriptor.contract_id]
    except KeyError as error:
        raise ContractSchemaError(
            f"no canonical model is registered for {descriptor.contract_id}"
        ) from error
    _verify_model_identity(model, descriptor)
    schema = cast(
        dict[str, Any],
        _remove_schema_descriptions(model.model_json_schema(mode="validation")),
    )
    schema["$schema"] = _SCHEMA_DRAFT
    schema["$id"] = _SCHEMA_ID_BASE + descriptor.schema_path
    return schema


def validate_contract_schemas(repository_root: Path = Path(".")) -> list[dict[str, str]]:
    """Return all catalog/model/schema discrepancies without mutating files."""
    catalog_path = repository_root / "governance" / "contract-catalog.yaml"
    registry = compile_contract_registry(
        catalog_path,
        repository_root=repository_root,
    )
    findings: list[dict[str, str]] = []
    for descriptor in registry.contracts.values():
        schema_path = repository_root / descriptor.schema_path
        if not schema_path.is_file():
            findings.append(
                {
                    "contract_id": descriptor.contract_id,
                    "path": descriptor.schema_path,
                    "rule": "catalog schema file is missing",
                }
            )
            continue
        try:
            committed = json.loads(schema_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            findings.append(
                {
                    "contract_id": descriptor.contract_id,
                    "path": descriptor.schema_path,
                    "rule": f"schema file is unreadable or invalid JSON: {error}",
                }
            )
            continue
        try:
            expected = expected_contract_schema(descriptor)
        except ContractSchemaError as error:
            findings.append(
                {
                    "contract_id": descriptor.contract_id,
                    "path": descriptor.schema_path,
                    "rule": str(error),
                }
            )
            continue
        if committed != expected:
            findings.append(
                {
                    "contract_id": descriptor.contract_id,
                    "path": descriptor.schema_path,
                    "rule": "committed JSON Schema differs from canonical model",
                }
            )
    unregistered = sorted(set(_MODELS) - set(registry.contracts))
    findings.extend(
        {
            "contract_id": contract_id,
            "path": "governance/contract-catalog.yaml",
            "rule": "canonical model is not registered in the contract catalog",
        }
        for contract_id in unregistered
    )
    return findings


def require_valid_contract_schemas(repository_root: Path = Path(".")) -> None:
    """Fail closed when any canonical schema does not match its model."""
    findings = validate_contract_schemas(repository_root)
    if findings:
        summary = "; ".join(
            f"{item['contract_id']}:{item['rule']}" for item in findings
        )
        raise ContractSchemaError(summary)


def write_contract_schemas(repository_root: Path = Path(".")) -> None:
    """Write all catalog schemas using stable canonical formatting."""
    registry = compile_contract_registry(
        repository_root / "governance" / "contract-catalog.yaml",
        repository_root=repository_root,
    )
    for descriptor in registry.contracts.values():
        schema_path = repository_root / descriptor.schema_path
        schema_path.parent.mkdir(parents=True, exist_ok=True)
        schema_path.write_text(
            json.dumps(expected_contract_schema(descriptor), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def _verify_model_identity(
    model: type[BaseModel],
    descriptor: ContractDescriptor,
) -> None:
    contract_field = model.model_fields.get("contract_id")
    version_field = model.model_fields.get("schema_version")
    if contract_field is None or contract_field.default != descriptor.contract_id:
        raise ContractSchemaError(
            f"model contract ID disagrees with catalog: {descriptor.contract_id}"
        )
    if version_field is None or version_field.default != descriptor.schema_version:
        raise ContractSchemaError(
            f"model schema version disagrees with catalog: {descriptor.contract_id}"
        )


def _remove_schema_descriptions(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if key == "description":
                continue
            if key == "properties" and isinstance(item, dict):
                result[key] = {
                    property_name: _remove_schema_descriptions(property_schema)
                    for property_name, property_schema in item.items()
                }
            else:
                result[key] = _remove_schema_descriptions(item)
        return result
    if isinstance(value, list):
        return [_remove_schema_descriptions(item) for item in value]
    return value
