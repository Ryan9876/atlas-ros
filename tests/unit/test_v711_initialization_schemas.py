from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from atlas_ros.contracts.authority import (
    InitializationReceipt,
    IntegrationInventorySnapshot,
    SystemStateSnapshot,
)


SCHEMAS: tuple[tuple[str, type[BaseModel]], ...] = (
    (
        "schemas/authority/system-state-initialization-projection.schema.json",
        SystemStateSnapshot,
    ),
    (
        "schemas/authority/integration-inventory-initialization-projection.schema.json",
        IntegrationInventorySnapshot,
    ),
    ("schemas/authority/initialization-receipt.schema.json", InitializationReceipt),
)


def test_v711_initialization_schemas_match_contracts() -> None:
    for filename, model in SCHEMAS:
        generated = model.model_json_schema()
        generated["$schema"] = "https://json-schema.org/draft/2020-12/schema"
        generated["$id"] = "https://github.com/Ryan9876/atlas-ros/" + filename
        committed = json.loads(Path(filename).read_text(encoding="utf-8"))
        assert committed == generated
