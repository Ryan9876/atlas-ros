from __future__ import annotations

import json
from pathlib import Path

from atlas_ros.contracts import (
    CheckpointToken,
    FieldAuthorityRegistry,
    ReconciliationAuthorization,
    ReconciliationConflict,
    ReconciliationMutationV2,
    ReconciliationPlanV2,
    ReconciliationReceiptV2,
    ReconciliationSnapshot,
)

MODELS = {
    "field-authority-registry-v2.schema.json": FieldAuthorityRegistry,
    "reconciliation-snapshot-v2.schema.json": ReconciliationSnapshot,
    "reconciliation-mutation-v2.schema.json": ReconciliationMutationV2,
    "reconciliation-conflict-v2.schema.json": ReconciliationConflict,
    "checkpoint-token-v2.schema.json": CheckpointToken,
    "reconciliation-plan-v2.schema.json": ReconciliationPlanV2,
    "reconciliation-authorization-v2.schema.json": ReconciliationAuthorization,
    "reconciliation-receipt-v2.schema.json": ReconciliationReceiptV2,
}


def main() -> None:
    output = Path("schemas/reconciliation")
    output.mkdir(parents=True, exist_ok=True)
    for name, model in MODELS.items():
        (output / name).write_text(
            json.dumps(model.model_json_schema(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
