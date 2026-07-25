from __future__ import annotations

import json
from pathlib import Path

from atlas_ros.contracts import (
    ExecutionAuthorizationV2,
    ExecutionCommandV2,
    ExecutionReceiptV2,
    ExecutionTransactionV2,
    ProviderOperation,
)

MODELS = {
    "execution-authorization-v2.schema.json": ExecutionAuthorizationV2,
    "execution-command-v2.schema.json": ExecutionCommandV2,
    "execution-transaction-v2.schema.json": ExecutionTransactionV2,
    "provider-operation-v2.schema.json": ProviderOperation,
    "execution-receipt-v2.schema.json": ExecutionReceiptV2,
}


def main() -> None:
    target = Path("schemas/orchestration")
    target.mkdir(parents=True, exist_ok=True)
    for filename, model in MODELS.items():
        schema = model.model_json_schema()
        schema["$id"] = f"https://atlas-ros.local/schemas/orchestration/{filename}"
        target.joinpath(filename).write_text(
            json.dumps(schema, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


if __name__ == "__main__":
    main()
