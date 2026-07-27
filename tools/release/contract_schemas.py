"""Generate and verify canonical JSON Schemas for the v7 contract catalog."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from atlas_ros.contracts.execution.pipeline import CaptureEnvelope, PipelineRunEnvelope
from atlas_ros.contracts.execution.transaction import (
    AuthorizedExecutionPlan,
    ExecutionTransactionReceipt,
)
from atlas_ros.contracts.v62 import IntentGraph

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DRAFT = "https://json-schema.org/draft/2020-12/schema"
_MODELS: Mapping[str, type[BaseModel]] = {
    "schemas/capture/capture-envelope.schema.json": CaptureEnvelope,
    "schemas/reasoning/intent-graph.schema.json": IntentGraph,
    "schemas/execution/authorized-execution-plan.schema.json": AuthorizedExecutionPlan,
    "schemas/execution/execution-transaction-receipt.schema.json": (
        ExecutionTransactionReceipt
    ),
    "schemas/execution/pipeline-run-envelope.schema.json": PipelineRunEnvelope,
}


class ContractSchemaError(ValueError):
    """Raised when committed contract schemas disagree with typed models."""


def generate_schemas() -> dict[str, dict[str, Any]]:
    """Return canonical schemas keyed by repository-relative path."""
    generated: dict[str, dict[str, Any]] = {}
    for path, model in _MODELS.items():
        schema = _remove_descriptions(model.model_json_schema(mode="validation"))
        schema["$schema"] = SCHEMA_DRAFT
        schema["$id"] = f"https://github.com/Ryan9876/atlas-ros/{path}"
        generated[path] = _sorted_mapping(schema)
    return generated


def check_schemas(root: Path = ROOT) -> None:
    """Fail if any committed catalog schema is missing or differs from its model."""
    for relative, expected in generate_schemas().items():
        path = root / relative
        if not path.is_file():
            raise ContractSchemaError(f"contract schema is missing: {relative}")
        try:
            actual = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ContractSchemaError(f"contract schema is invalid JSON: {relative}") from error
        if _sorted_mapping(actual) != expected:
            raise ContractSchemaError(f"contract schema drift detected: {relative}")


def write_schemas(root: Path = ROOT) -> None:
    """Write canonical schemas using stable formatting."""
    for relative, schema in generate_schemas().items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(schema, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def _remove_descriptions(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _remove_descriptions(item)
            for key, item in value.items()
            if key != "description"
        }
    if isinstance(value, list):
        return [_remove_descriptions(item) for item in value]
    return value


def _sorted_mapping(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sorted_mapping(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_sorted_mapping(item) for item in value]
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if args.check:
        check_schemas()
    else:
        write_schemas()


if __name__ == "__main__":
    main()
